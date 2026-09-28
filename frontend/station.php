<?php
session_start();

require_once __DIR__ . '/../config/class.connect.php';

$db = new connect();
$rows = [];
$stationTypes = [];
$errorMessage = '';
$recordsPerPage = 50;

$search = isset($_GET['search']) ? trim($_GET['search']) : '';
$typeId = isset($_GET['type']) ? (int) $_GET['type'] : 0;
$status = isset($_GET['status']) && $_GET['status'] !== '' ? (int) $_GET['status'] : -1;
$currentPage = max(1, isset($_GET['page']) ? (int) $_GET['page'] : 1);
$offset = ($currentPage - 1) * $recordsPerPage;

$totalRecords = 0;
$activeRecords = 0;
$totalTypes = 0;
$avgDepth = null;
$minDepth = null;
$maxDepth = null;
$totalPages = 1;

try {
    $conn = $db->conn();
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $typeStatement = $conn->query("SELECT id, name FROM station_type WHERE status = 1 ORDER BY name ASC");
    $stationTypes = $typeStatement->fetchAll(PDO::FETCH_ASSOC);

    $where = [];
    $parameters = [];

    if ($typeId > 0) {
        $where[] = 's.type = :type';
        $parameters[':type'] = $typeId;
    }

    if ($status === 0 || $status === 1) {
        $where[] = 's.status = :status';
        $parameters[':status'] = $status;
    }

    if ($search !== '') {
        $where[] = "(
            CAST(s.id AS CHAR) LIKE :search
            OR s.station_name LIKE :search
            OR CAST(s.latitude AS CHAR) LIKE :search
            OR CAST(s.longitude AS CHAR) LIKE :search
            OR CAST(s.depth AS CHAR) LIKE :search
            OR st.name LIKE :search
            OR st.detail LIKE :search
        )";
        $parameters[':search'] = '%' . $search . '%';
    }

    $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

    $summarySql = "
        SELECT COUNT(*) AS total_records,
               SUM(CASE WHEN s.status = 1 THEN 1 ELSE 0 END) AS active_records,
               COUNT(DISTINCT s.type) AS total_types,
               AVG(s.depth) AS avg_depth,
               MIN(s.depth) AS min_depth,
               MAX(s.depth) AS max_depth
        FROM station AS s
        LEFT JOIN station_type AS st ON st.id = s.type
        $whereSql
    ";
    $summaryStatement = $conn->prepare($summarySql);
    foreach ($parameters as $key => $value) {
        $summaryStatement->bindValue($key, $value, is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR);
    }
    $summaryStatement->execute();
    $summary = $summaryStatement->fetch(PDO::FETCH_ASSOC);

    $totalRecords = (int) ($summary['total_records'] ?? 0);
    $activeRecords = (int) ($summary['active_records'] ?? 0);
    $totalTypes = (int) ($summary['total_types'] ?? 0);
    $avgDepth = $summary['avg_depth'] !== null ? (float) $summary['avg_depth'] : null;
    $minDepth = $summary['min_depth'] !== null ? (float) $summary['min_depth'] : null;
    $maxDepth = $summary['max_depth'] !== null ? (float) $summary['max_depth'] : null;

    $totalPages = max(1, (int) ceil($totalRecords / $recordsPerPage));
    if ($currentPage > $totalPages) {
        $currentPage = $totalPages;
        $offset = ($currentPage - 1) * $recordsPerPage;
    }

    $dataSql = "
        SELECT s.id, s.station_name, s.latitude, s.longitude, s.depth,
               s.type, s.status, st.name AS type_name, st.detail AS type_detail
        FROM station AS s
        LEFT JOIN station_type AS st ON st.id = s.type
        $whereSql
        ORDER BY s.id ASC
        LIMIT :records_per_page OFFSET :record_offset
    ";
    $dataStatement = $conn->prepare($dataSql);
    foreach ($parameters as $key => $value) {
        $dataStatement->bindValue($key, $value, is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR);
    }
    $dataStatement->bindValue(':records_per_page', $recordsPerPage, PDO::PARAM_INT);
    $dataStatement->bindValue(':record_offset', $offset, PDO::PARAM_INT);
    $dataStatement->execute();
    $rows = $dataStatement->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $exception) {
    $errorMessage = 'Database error: ' . $exception->getMessage();
} catch (Throwable $exception) {
    $errorMessage = 'System error: ' . $exception->getMessage();
}

function buildStationPageUrl(int $page, string $search, int $typeId, int $status): string
{
    return '?' . http_build_query([
        'search' => $search,
        'type' => $typeId,
        'status' => $status === -1 ? '' : $status,
        'page' => $page
    ]);
}
?>
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Station Data | ARCHRIVE</title>
    <link rel="icon" type="image/png" href="../img/logo.png">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="../css/menu.css">
    <link rel="stylesheet" href="../css/data.css">
    <style>
        .metric-card { border: 0; border-radius: 12px; }
        .metric-value { font-size: 1.7rem; font-weight: 700; }
        .metric-sub { font-size: .85rem; }
        .filter-label { font-weight: 600; margin-bottom: 6px; }
        .station-table th, .station-table td { white-space: nowrap; }
        .station-table .detail-column { white-space: normal; min-width: 220px; }
    </style>
</head>
<body>
<?php include 'menu.php'; ?>

<div class="container page-container">
    <div class="mb-4">
        <h2 class="page-title mb-1">ข้อมูลพื้นที่และสถานี</h2>
        <p class="text-muted mb-0">แสดงพิกัด ความลึก และประเภทของแต่ละพื้นที่</p>
    </div>

    <div class="row mb-4">
        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100"><div class="card-body text-center">
                <h6 class="text-muted">พื้นที่ทั้งหมด</h6>
                <div class="metric-value text-primary"><?= number_format($totalRecords) ?></div>
                <div class="metric-sub text-muted"><?= number_format($activeRecords) ?> พื้นที่ที่ใช้งาน</div>
            </div></div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100"><div class="card-body text-center">
                <h6 class="text-muted">ประเภทสถานี</h6>
                <div class="metric-value text-primary"><?= number_format($totalTypes) ?></div>
                <div class="metric-sub text-muted">ประเภทในผลลัพธ์ปัจจุบัน</div>
            </div></div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100"><div class="card-body text-center">
                <h6 class="text-muted">ความลึกเฉลี่ย</h6>
                <div class="metric-value text-primary"><?= $avgDepth !== null ? number_format($avgDepth, 2) . ' m' : '-' ?></div>
                <div class="metric-sub text-muted">Min: <?= $minDepth !== null ? number_format($minDepth, 2) . ' m' : '-' ?>
                 · Max: <?= $maxDepth !== null ? number_format($maxDepth, 2) . ' m' : '-' ?></div>
            </div></div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100"><div class="card-body text-center">
                <h6 class="text-muted">ความลึกสูงสุด</h6>
                <div class="metric-value text-primary"><?= $maxDepth !== null ? number_format($maxDepth, 2) . ' m' : '-' ?></div>
                <div class="metric-sub text-muted">จากผลลัพธ์ปัจจุบัน</div>
            </div></div>
        </div>
    </div>

    <?php if ($errorMessage !== ''): ?>
        <div class="alert alert-danger"><?= htmlspecialchars($errorMessage, ENT_QUOTES, 'UTF-8') ?></div>
    <?php endif; ?>

    <div class="card shadow-sm border-0 mb-4"><div class="card-body">
        <form method="get" action="station.php">
            <div class="row g-2">
                <div class="col-md-3">
                    <label class="filter-label">ประเภทสถานี</label>
                    <select name="type" class="form-select">
                        <option value="0">ทุกประเภท</option>
                        <?php foreach ($stationTypes as $stationType): ?>
                            <option value="<?= (int) $stationType['id'] ?>" <?= $typeId === (int) $stationType['id'] ? 'selected' : '' ?>>
                                <?= htmlspecialchars($stationType['name'], ENT_QUOTES, 'UTF-8') ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="filter-label">สถานะ</label>
                    <select name="status" class="form-select">
                        <option value="" <?= $status === -1 ? 'selected' : '' ?>>ทุกสถานะ</option>
                        <option value="1" <?= $status === 1 ? 'selected' : '' ?>>Active</option>
                        <option value="0" <?= $status === 0 ? 'selected' : '' ?>>Inactive</option>
                    </select>
                </div>
                <div class="col-md-5">
                    <label class="filter-label">ค้นหา</label>
                    <input type="text" name="search" class="form-control"
                           placeholder="จังหวัด, พิกัด, ความลึก หรือประเภทสถานี..."
                           value="<?= htmlspecialchars($search, ENT_QUOTES, 'UTF-8') ?>">
                </div>
                <div class="col-md-2 d-flex align-items-end gap-2">
                    <button type="submit" class="btn btn-primary flex-fill">ค้นหา</button>
                    <a href="station.php" class="btn btn-secondary">ล้าง</a>
                </div>
            </div>
        </form>
    </div></div>

    <div class="card shadow-sm border-0"><div class="card-body">
        <div class="d-flex justify-content-between align-items-center flex-wrap mb-3">
            <div><h5 class="mb-1">ตารางข้อมูลพื้นที่และสถานี</h5><small class="text-muted">ข้อมูลประจำพื้นที่จากตาราง station</small></div>
            <span class="text-muted">หน้า <?= number_format($currentPage) ?> จาก <?= number_format($totalPages) ?></span>
        </div>
        <div class="table-responsive">
            <table class="table table-striped table-hover table-bordered align-middle station-table">
                <thead class="table-light"><tr>
                    <th>ID</th><th>จังหวัด</th><th>Latitude</th><th>Longitude</th>
                    <th class="text-end">Depth (m)</th><th>ประเภท</th><th class="detail-column">รายละเอียด</th><th>สถานะ</th>
                </tr></thead>
                <tbody>
                <?php if ($rows): foreach ($rows as $row): ?>
                    <tr>
                        <td><?= (int) $row['id'] ?></td>
                        <td><?= htmlspecialchars($row['station_name'] ?? '-', ENT_QUOTES, 'UTF-8') ?></td>
                        <td><?= $row['latitude'] !== null ? number_format((float) $row['latitude'], 6) : '-' ?></td>
                        <td><?= $row['longitude'] !== null ? number_format((float) $row['longitude'], 6) : '-' ?></td>
                        <td class="text-end fw-semibold"><?= $row['depth'] !== null ? number_format((float) $row['depth'], 2) : '-' ?></td>
                        <td><?= htmlspecialchars($row['type_name'] ?? 'ไม่ระบุ', ENT_QUOTES, 'UTF-8') ?></td>
                        <td class="detail-column"><?= htmlspecialchars($row['type_detail'] ?? '-', ENT_QUOTES, 'UTF-8') ?></td>
                        <td><?= (int) $row['status'] === 1 ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-secondary">Inactive</span>' ?></td>
                    </tr>
                <?php endforeach; else: ?>
                    <tr><td colspan="8" class="text-center text-muted py-4">ไม่พบข้อมูล</td></tr>
                <?php endif; ?>
                </tbody>
            </table>
        </div>

        <?php if ($totalPages > 1):
            $startPage = max(1, $currentPage - 2);
            $endPage = min($totalPages, $currentPage + 2); ?>
            <nav class="mt-4"><ul class="pagination justify-content-center flex-wrap">
                <li class="page-item <?= $currentPage <= 1 ? 'disabled' : '' ?>">
                    <a class="page-link" href="<?= $currentPage > 1 ? htmlspecialchars(buildStationPageUrl($currentPage - 1, $search, $typeId, $status), ENT_QUOTES, 'UTF-8') : '#' ?>">ก่อนหน้า</a>
                </li>
                <?php for ($pageNumber = $startPage; $pageNumber <= $endPage; $pageNumber++): ?>
                    <li class="page-item <?= $pageNumber === $currentPage ? 'active' : '' ?>">
                        <a class="page-link" href="<?= htmlspecialchars(buildStationPageUrl($pageNumber, $search, $typeId, $status), ENT_QUOTES, 'UTF-8') ?>"><?= $pageNumber ?></a>
                    </li>
                <?php endfor; ?>
                <li class="page-item <?= $currentPage >= $totalPages ? 'disabled' : '' ?>">
                    <a class="page-link" href="<?= $currentPage < $totalPages ? htmlspecialchars(buildStationPageUrl($currentPage + 1, $search, $typeId, $status), ENT_QUOTES, 'UTF-8') : '#' ?>">ถัดไป</a>
                </li>
            </ul></nav>
        <?php endif; ?>

        <?php if ($totalRecords > 0): ?>
            <p class="text-center text-muted mb-0">
                แสดงรายการที่ <?= number_format($offset + 1) ?> ถึง <?= number_format(min($offset + $recordsPerPage, $totalRecords)) ?>
                จากทั้งหมด <?= number_format($totalRecords) ?> รายการ
            </p>
        <?php endif; ?>
    </div></div>
</div>

<?php include 'footer.php'; ?>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
