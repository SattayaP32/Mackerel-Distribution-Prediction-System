<?php
session_start();

require_once __DIR__ . '/../config/class.connect.php';

$db = new connect();

$rows = [];
$errorMessage = '';

$recordsPerPage = 50;

/* =====================================
   รับค่าจากตัวกรอง
===================================== */
$search = isset($_GET['search']) ? trim($_GET['search']) : '';
$statusFilter = isset($_GET['status_filter']) ? trim($_GET['status_filter']) : 'all';
$stationId = isset($_GET['station_id']) ? (int) $_GET['station_id'] : 0;
$year = isset($_GET['year']) ? (int) $_GET['year'] : 0;
$month = isset($_GET['month']) ? (int) $_GET['month'] : 0;

if (!in_array($statusFilter, ['all', 'active', 'inactive'], true)) {
    $statusFilter = 'all';
}

$currentPage = isset($_GET['page']) ? (int) $_GET['page'] : 1;
if ($currentPage < 1) {
    $currentPage = 1;
}

$offset = ($currentPage - 1) * $recordsPerPage;

$totalRecords = 0;
$totalStations = 0;
$minimumYear = null;
$maximumYear = null;
$totalPages = 1;

$avgAmount = null;
$minAmount = null;
$maxAmount = null;
$totalAmount = null;

$stations = [];
$years = [];

$monthNames = [
    1 => 'มกราคม',
    2 => 'กุมภาพันธ์',
    3 => 'มีนาคม',
    4 => 'เมษายน',
    5 => 'พฤษภาคม',
    6 => 'มิถุนายน',
    7 => 'กรกฎาคม',
    8 => 'สิงหาคม',
    9 => 'กันยายน',
    10 => 'ตุลาคม',
    11 => 'พฤศจิกายน',
    12 => 'ธันวาคม'
];

$monthSearchMap = [
    'มกราคม' => 1, 'กุมภาพันธ์' => 2, 'มีนาคม' => 3,
    'เมษายน' => 4, 'พฤษภาคม' => 5, 'มิถุนายน' => 6,
    'กรกฎาคม' => 7, 'สิงหาคม' => 8, 'กันยายน' => 9,
    'ตุลาคม' => 10, 'พฤศจิกายน' => 11, 'ธันวาคม' => 12,
    'january' => 1, 'february' => 2, 'march' => 3,
    'april' => 4, 'may' => 5, 'june' => 6,
    'july' => 7, 'august' => 8, 'september' => 9,
    'october' => 10, 'november' => 11, 'december' => 12,
    'jan' => 1, 'feb' => 2, 'mar' => 3, 'apr' => 4,
    'jun' => 6, 'jul' => 7, 'aug' => 8, 'sep' => 9,
    'sept' => 9, 'oct' => 10, 'nov' => 11, 'dec' => 12
];

try {
    $conn = $db->conn();
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    /* =====================================
       รายการจังหวัดและปี
    ===================================== */
    $stationStatement = $conn->query("
        SELECT id, station_name
        FROM station
        WHERE status = 1
        ORDER BY station_name ASC
    ");
    $stations = $stationStatement->fetchAll(PDO::FETCH_ASSOC);

    $yearStatement = $conn->query("
        SELECT DISTINCT year
        FROM catch_mackereldata
        ORDER BY year DESC
    ");
    $years = $yearStatement->fetchAll(PDO::FETCH_COLUMN);

    /* =====================================
       เงื่อนไขค้นหา / ตัวกรอง
    ===================================== */
    $where = ['1 = 1'];
    $parameters = [];

    if ($statusFilter === 'active') {
        $where[] = 'cmd.status = 1';
    } elseif ($statusFilter === 'inactive') {
        $where[] = 'cmd.status = 0';
    }

    if ($stationId > 0) {
        $where[] = 'cmd.station_id = :station_id';
        $parameters[':station_id'] = $stationId;
    }

    if ($year > 0) {
        $where[] = 'cmd.year = :year';
        $parameters[':year'] = $year;
    }

    if ($month >= 1 && $month <= 12) {
        $where[] = 'cmd.month = :month';
        $parameters[':month'] = $month;
    }

    if ($search !== '') {
        $normalizedSearch = mb_strtolower(trim($search), 'UTF-8');
        $searchedMonth = $monthSearchMap[$normalizedSearch] ?? null;

        if ($searchedMonth !== null) {
            $where[] = 'cmd.month = :searched_month';
            $parameters[':searched_month'] = $searchedMonth;
        } else {
            $where[] = "(
                CAST(cmd.id AS CHAR) LIKE :search
                OR s.station_name LIKE :search
                OR CAST(cmd.year AS CHAR) LIKE :search
                OR CAST(cmd.month AS CHAR) LIKE :search
                OR CAST(cmd.amount AS CHAR) LIKE :search
                OR cmd.unit LIKE :search
                OR e.name LIKE :search
                OR CAST(cmd.status AS CHAR) LIKE :search
            )";
            $parameters[':search'] = '%' . $search . '%';
        }
    }

    $whereSql = 'WHERE ' . implode(' AND ', $where);

    /* =====================================
       จำนวนข้อมูล
    ===================================== */
    $countSql = "
        SELECT COUNT(*) AS total_records
        FROM catch_mackereldata AS cmd
        LEFT JOIN station AS s ON s.id = cmd.station_id
        LEFT JOIN equipment AS e ON e.id = cmd.equipment_id
        $whereSql
    ";

    $countStatement = $conn->prepare($countSql);
    foreach ($parameters as $key => $value) {
        $countStatement->bindValue(
            $key,
            $value,
            is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR
        );
    }
    $countStatement->execute();

    $countResult = $countStatement->fetch(PDO::FETCH_ASSOC);
    $totalRecords = (int) ($countResult['total_records'] ?? 0);

    $totalPages = max(1, (int) ceil($totalRecords / $recordsPerPage));

    if ($currentPage > $totalPages) {
        $currentPage = $totalPages;
        $offset = ($currentPage - 1) * $recordsPerPage;
    }

    /* =====================================
       สถิติปริมาณปลาทู
    ===================================== */
    $statsSql = "
        SELECT
            AVG(cmd.amount) AS avg_amount,
            MIN(cmd.amount) AS min_amount,
            MAX(cmd.amount) AS max_amount,
            SUM(cmd.amount) AS total_amount
        FROM catch_mackereldata AS cmd
        LEFT JOIN station AS s ON s.id = cmd.station_id
        LEFT JOIN equipment AS e ON e.id = cmd.equipment_id
        $whereSql
    ";

    $statsStatement = $conn->prepare($statsSql);
    foreach ($parameters as $key => $value) {
        $statsStatement->bindValue(
            $key,
            $value,
            is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR
        );
    }
    $statsStatement->execute();

    $stats = $statsStatement->fetch(PDO::FETCH_ASSOC);

    $avgAmount = $stats['avg_amount'] !== null ? (float) $stats['avg_amount'] : null;
    $minAmount = $stats['min_amount'] !== null ? (float) $stats['min_amount'] : null;
    $maxAmount = $stats['max_amount'] !== null ? (float) $stats['max_amount'] : null;
    $totalAmount = $stats['total_amount'] !== null ? (float) $stats['total_amount'] : null;

    /* =====================================
       จำนวนจังหวัดตามผลลัพธ์
    ===================================== */
    $stationCountSql = "
        SELECT COUNT(DISTINCT cmd.station_id) AS total_stations
        FROM catch_mackereldata AS cmd
        LEFT JOIN station AS s ON s.id = cmd.station_id
        LEFT JOIN equipment AS e ON e.id = cmd.equipment_id
        $whereSql
    ";

    $stationCountStatement = $conn->prepare($stationCountSql);
    foreach ($parameters as $key => $value) {
        $stationCountStatement->bindValue(
            $key,
            $value,
            is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR
        );
    }
    $stationCountStatement->execute();

    $stationCountResult = $stationCountStatement->fetch(PDO::FETCH_ASSOC);
    $totalStations = (int) ($stationCountResult['total_stations'] ?? 0);

    /* =====================================
       ช่วงปีตามผลลัพธ์
    ===================================== */
    $yearRangeSql = "
        SELECT
            MIN(cmd.year) AS minimum_year,
            MAX(cmd.year) AS maximum_year
        FROM catch_mackereldata AS cmd
        LEFT JOIN station AS s ON s.id = cmd.station_id
        LEFT JOIN equipment AS e ON e.id = cmd.equipment_id
        $whereSql
    ";

    $yearRangeStatement = $conn->prepare($yearRangeSql);
    foreach ($parameters as $key => $value) {
        $yearRangeStatement->bindValue(
            $key,
            $value,
            is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR
        );
    }
    $yearRangeStatement->execute();

    $yearRange = $yearRangeStatement->fetch(PDO::FETCH_ASSOC);

    if ($yearRange && $yearRange['minimum_year'] !== null) {
        $minimumYear = (int) $yearRange['minimum_year'];
        $maximumYear = (int) $yearRange['maximum_year'];
    }

    /* =====================================
       ดึงข้อมูล
    ===================================== */
    $dataSql = "
        SELECT
            cmd.id,
            cmd.station_id,
            s.station_name AS province,
            cmd.year,
            cmd.month,
            cmd.amount,
            cmd.unit,
            e.name AS equipment_name,
            cmd.status
        FROM catch_mackereldata AS cmd
        LEFT JOIN station AS s ON s.id = cmd.station_id
        LEFT JOIN equipment AS e ON e.id = cmd.equipment_id
        $whereSql
        ORDER BY cmd.id ASC
        LIMIT :records_per_page
        OFFSET :record_offset
    ";

    $dataStatement = $conn->prepare($dataSql);

    foreach ($parameters as $key => $value) {
        $dataStatement->bindValue(
            $key,
            $value,
            is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR
        );
    }

    $dataStatement->bindValue(
        ':records_per_page',
        $recordsPerPage,
        PDO::PARAM_INT
    );

    $dataStatement->bindValue(
        ':record_offset',
        $offset,
        PDO::PARAM_INT
    );

    $dataStatement->execute();
    $rows = $dataStatement->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $exception) {
    $errorMessage = 'Database error: ' . $exception->getMessage();

} catch (Throwable $exception) {
    $errorMessage = 'System error: ' . $exception->getMessage();
}

/* =====================================
   URL สำหรับ Pagination
===================================== */
function buildPageUrl(
    int $page,
    string $search,
    string $statusFilter,
    int $stationId,
    int $year,
    int $month
): string {
    return '?' . http_build_query([
        'search' => $search,
        'status_filter' => $statusFilter,
        'station_id' => $stationId,
        'year' => $year,
        'month' => $month,
        'page' => $page
    ]);
}
?>

<!DOCTYPE html>
<html lang="th">

<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Mackerel Dataset | ARCHRIVE</title>

    <link rel="icon" type="image/png" href="../img/logo.png">
    
    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet"
    >

    <link
        rel="stylesheet"
        href="../css/menu.css"
    >

    <link
        rel="stylesheet"
        href="../css/data.css"
    >

    <style>
        .metric-card {
            border: 0;
            border-radius: 12px;
        }

        .metric-value {
            font-size: 1.7rem;
            font-weight: 700;
        }

        .metric-sub {
            font-size: 0.85rem;
        }

        .filter-label {
            font-weight: 600;
            margin-bottom: 6px;
        }

        .metric-tabs .btn {
            min-width: 110px;
        }

        .dataset-table th,
        .dataset-table td {
            white-space: nowrap;
        }

        .value-amount {
            font-weight: 600;
        }
    </style>
</head>

<body>

<?php include 'menu.php'; ?>

<div class="container page-container">

    <!-- Header -->
    <div class="mb-4">
        <h2 class="page-title mb-1">
            ข้อมูลจำนวนปลาทู
        </h2>

        <p class="text-muted mb-0">
            แสดงข้อมูลปริมาณการจับปลาทู จำแนกตามจังหวัด ปี เดือน และเครื่องมือประมง
        </p>
    </div>

    <!-- Summary -->
    <div class="row mb-4">

        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100">
                <div class="card-body text-center">
                    <h6 class="text-muted">ข้อมูลทั้งหมด</h6>

                    <div class="metric-value text-primary">
                        <?= number_format($totalRecords) ?>
                    </div>

                    <div class="metric-sub text-muted">รายการตามตัวกรองที่เลือก</div>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100">
                <div class="card-body text-center">
                    <h6 class="text-muted">จังหวัดที่มีข้อมูล</h6>

                    <div class="metric-value text-primary">
                        <?= number_format($totalStations) ?>
                    </div>

                    <div class="metric-sub text-muted">
                        <?php if ($minimumYear !== null): ?>
                            ช่วงปี <?= $minimumYear ?> - <?= $maximumYear ?>
                        <?php else: ?>
                            ไม่พบช่วงปีของข้อมูล
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100">
                <div class="card-body text-center">
                    <h6 class="text-muted">ปริมาณเฉลี่ย</h6>

                    <div class="metric-value text-primary">
                        <?= $avgAmount !== null
                            ? number_format($avgAmount, 2) . ' ตัน'
                            : '-' ?>
                    </div>

                    <div class="metric-sub text-muted">
                        Min:
                        <?= $minAmount !== null ? number_format($minAmount, 2) . ' ตัน' : '-' ?>
                        · Max:
                        <?= $maxAmount !== null ? number_format($maxAmount, 2) . ' ตัน' : '-' ?>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card metric-card shadow-sm h-100">
                <div class="card-body text-center">
                    <h6 class="text-muted">ปริมาณรวม</h6>

                    <div class="metric-value text-primary">
                        <?= $totalAmount !== null
                            ? number_format($totalAmount, 2) . ' ตัน'
                            : '-' ?>
                    </div>

                    <div class="metric-sub text-muted">
                        คำนวณจากข้อมูลตามตัวกรองที่เลือก
                    </div>
                </div>
            </div>
        </div>

    </div>

    <?php if ($errorMessage !== ''): ?>
        <div class="alert alert-danger">
            <?= htmlspecialchars($errorMessage, ENT_QUOTES, 'UTF-8') ?>
        </div>
    <?php endif; ?>

    <!-- Filter -->
    <div class="card shadow-sm border-0 mb-4">
        <div class="card-body">

            <form method="get" action="dataset.php">

                <div class="mb-3">
                    <div class="filter-label">
                        เลือกสถานะข้อมูล
                    </div>

                    <div class="btn-group metric-tabs flex-wrap" role="group">

                        <input
                            type="radio"
                            class="btn-check"
                            name="status_filter"
                            id="statusAll"
                            value="all"
                            <?= $statusFilter === 'all' ? 'checked' : '' ?>
                        >
                        <label class="btn btn-outline-primary" for="statusAll">
                            ทั้งหมด
                        </label>

                        <input
                            type="radio"
                            class="btn-check"
                            name="status_filter"
                            id="statusActive"
                            value="active"
                            <?= $statusFilter === 'active' ? 'checked' : '' ?>
                        >
                        <label class="btn btn-outline-primary" for="statusActive">
                            Active
                        </label>

                        <input
                            type="radio"
                            class="btn-check"
                            name="status_filter"
                            id="statusInactive"
                            value="inactive"
                            <?= $statusFilter === 'inactive' ? 'checked' : '' ?>
                        >
                        <label class="btn btn-outline-primary" for="statusInactive">
                            Inactive
                        </label>

                    </div>
                </div>

                <div class="row g-2">

                    <div class="col-lg-3 col-md-6">
                        <label class="filter-label">จังหวัด</label>

                        <select name="station_id" class="form-select">
                            <option value="0">ทุกจังหวัด</option>

                            <?php foreach ($stations as $station): ?>
                                <option
                                    value="<?= (int) $station['id'] ?>"
                                    <?= $stationId === (int) $station['id'] ? 'selected' : '' ?>
                                >
                                    <?= htmlspecialchars(
                                        $station['station_name'] ?? '-',
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <div class="col-lg-2 col-md-6">
                        <label class="filter-label">ปี</label>

                        <select name="year" class="form-select">
                            <option value="0">ทุกปี</option>

                            <?php foreach ($years as $availableYear): ?>
                                <option
                                    value="<?= (int) $availableYear ?>"
                                    <?= $year === (int) $availableYear ? 'selected' : '' ?>
                                >
                                    <?= (int) $availableYear ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <div class="col-lg-2 col-md-6">
                        <label class="filter-label">เดือน</label>

                        <select name="month" class="form-select">
                            <option value="0">ทุกเดือน</option>

                            <?php foreach ($monthNames as $monthNumber => $monthName): ?>
                                <option
                                    value="<?= $monthNumber ?>"
                                    <?= $month === $monthNumber ? 'selected' : '' ?>
                                >
                                    <?= htmlspecialchars($monthName, ENT_QUOTES, 'UTF-8') ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <div class="col-lg-3 col-md-6">
                        <label class="filter-label">ค้นหา</label>

                        <input
                            type="text"
                            name="search"
                            class="form-control"
                            placeholder="จังหวัด, ปี, เดือน, ปริมาณ หรือเครื่องมือ..."
                            value="<?= htmlspecialchars($search, ENT_QUOTES, 'UTF-8') ?>"
                        >
                    </div>

                    <div class="col-lg-2 col-md-12 d-flex align-items-end gap-2">
                        <button
                            type="submit"
                            class="btn btn-primary flex-fill"
                        >
                            ค้นหา
                        </button>

                        <a
                            href="dataset.php"
                            class="btn btn-secondary"
                        >
                            ล้าง
                        </a>
                    </div>

                </div>

            </form>
        </div>
    </div>

    <!-- Table -->
    <div class="card shadow-sm border-0">

        <div class="card-body">

            <div class="d-flex justify-content-between align-items-center flex-wrap mb-3">
                <div>
                    <h5 class="mb-1">
                        ตารางข้อมูลปริมาณปลาทู
                    </h5>

                    <small class="text-muted">
                        <?php if ($statusFilter === 'active'): ?>
                            แสดงเฉพาะข้อมูล Active
                        <?php elseif ($statusFilter === 'inactive'): ?>
                            แสดงเฉพาะข้อมูล Inactive
                        <?php else: ?>
                            แสดงข้อมูลทุกสถานะ
                        <?php endif; ?>
                    </small>
                </div>

                <span class="text-muted">
                    หน้า <?= number_format($currentPage) ?>
                    จาก <?= number_format($totalPages) ?>
                </span>
            </div>

            <div class="table-responsive">

                <table class="table table-striped table-hover table-bordered align-middle dataset-table">

                    <thead class="table-light">
                        <tr>
                            <th>ID</th>
                            <th>จังหวัด</th>
                            <th>ปี</th>
                            <th>เดือน</th>
                            <th class="text-end">ปริมาณ</th>
                            <th>หน่วย</th>
                            <th>เครื่องมือประมง</th>
                            <th>สถานะ</th>
                        </tr>
                    </thead>

                    <tbody>

                    <?php if (!empty($rows)): ?>

                        <?php foreach ($rows as $row): ?>

                            <?php
                                $monthNumber = (int) $row['month'];
                                $monthName = $monthNames[$monthNumber] ?? (string) $monthNumber;
                            ?>

                            <tr>

                                <td>
                                    <?= (int) $row['id'] ?>
                                </td>

                                <td>
                                    <?= htmlspecialchars(
                                        $row['province'] ?? '-',
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>
                                </td>

                                <td>
                                    <?= (int) $row['year'] ?>
                                </td>

                                <td>
                                    <?= htmlspecialchars(
                                        $monthName,
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>
                                </td>

                                <td class="text-end value-amount">
                                    <?= number_format(
                                        (float) $row['amount'],
                                        2
                                    ) ?>
                                </td>

                                <td>
                                    <?= htmlspecialchars(
                                        $row['unit'] ?? '-',
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>
                                </td>

                                <td>
                                    <?= htmlspecialchars(
                                        trim($row['equipment_name'] ?? '-'),
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>
                                </td>

                                <td>
                                    <?php if ((int) $row['status'] === 1): ?>
                                        <span class="badge bg-success">
                                            Active
                                        </span>
                                    <?php else: ?>
                                        <span class="badge bg-secondary">
                                            Inactive
                                        </span>
                                    <?php endif; ?>
                                </td>

                            </tr>

                        <?php endforeach; ?>

                    <?php else: ?>

                        <tr>
                            <td
                                colspan="8"
                                class="text-center text-muted py-4"
                            >
                                ไม่พบข้อมูล
                            </td>
                        </tr>

                    <?php endif; ?>

                    </tbody>

                </table>

            </div>

            <!-- Pagination -->
            <?php if ($totalPages > 1): ?>

                <?php
                    $startPage = max(1, $currentPage - 2);
                    $endPage = min($totalPages, $currentPage + 2);
                ?>

                <nav class="mt-4" aria-label="Dataset pagination">

                    <ul class="pagination justify-content-center flex-wrap">

                        <li class="page-item <?= $currentPage <= 1 ? 'disabled' : '' ?>">
                            <a
                                class="page-link"
                                href="<?= $currentPage > 1
                                    ? htmlspecialchars(
                                        buildPageUrl(
                                            $currentPage - 1,
                                            $search,
                                            $statusFilter,
                                            $stationId,
                                            $year,
                                            $month
                                        ),
                                        ENT_QUOTES,
                                        'UTF-8'
                                    )
                                    : '#' ?>"
                            >
                                ก่อนหน้า
                            </a>
                        </li>

                        <?php if ($startPage > 1): ?>

                            <li class="page-item">
                                <a
                                    class="page-link"
                                    href="<?= htmlspecialchars(
                                        buildPageUrl(
                                            1,
                                            $search,
                                            $statusFilter,
                                            $stationId,
                                            $year,
                                            $month
                                        ),
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>"
                                >
                                    1
                                </a>
                            </li>

                            <?php if ($startPage > 2): ?>
                                <li class="page-item disabled">
                                    <span class="page-link">...</span>
                                </li>
                            <?php endif; ?>

                        <?php endif; ?>

                        <?php for ($pageNumber = $startPage; $pageNumber <= $endPage; $pageNumber++): ?>

                            <li class="page-item <?= $pageNumber === $currentPage ? 'active' : '' ?>">
                                <a
                                    class="page-link"
                                    href="<?= htmlspecialchars(
                                        buildPageUrl(
                                            $pageNumber,
                                            $search,
                                            $statusFilter,
                                            $stationId,
                                            $year,
                                            $month
                                        ),
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>"
                                >
                                    <?= $pageNumber ?>
                                </a>
                            </li>

                        <?php endfor; ?>

                        <?php if ($endPage < $totalPages): ?>

                            <?php if ($endPage < $totalPages - 1): ?>
                                <li class="page-item disabled">
                                    <span class="page-link">...</span>
                                </li>
                            <?php endif; ?>

                            <li class="page-item">
                                <a
                                    class="page-link"
                                    href="<?= htmlspecialchars(
                                        buildPageUrl(
                                            $totalPages,
                                            $search,
                                            $statusFilter,
                                            $stationId,
                                            $year,
                                            $month
                                        ),
                                        ENT_QUOTES,
                                        'UTF-8'
                                    ) ?>"
                                >
                                    <?= $totalPages ?>
                                </a>
                            </li>

                        <?php endif; ?>

                        <li class="page-item <?= $currentPage >= $totalPages ? 'disabled' : '' ?>">
                            <a
                                class="page-link"
                                href="<?= $currentPage < $totalPages
                                    ? htmlspecialchars(
                                        buildPageUrl(
                                            $currentPage + 1,
                                            $search,
                                            $statusFilter,
                                            $stationId,
                                            $year,
                                            $month
                                        ),
                                        ENT_QUOTES,
                                        'UTF-8'
                                    )
                                    : '#' ?>"
                            >
                                ถัดไป
                            </a>
                        </li>

                    </ul>

                </nav>

            <?php endif; ?>

            <?php if ($totalRecords > 0): ?>

                <?php
                    $firstRecord = $offset + 1;
                    $lastRecord = min($offset + $recordsPerPage, $totalRecords);
                ?>

                <p class="text-center text-muted mb-0">
                    แสดงรายการที่
                    <?= number_format($firstRecord) ?>
                    ถึง
                    <?= number_format($lastRecord) ?>
                    จากทั้งหมด
                    <?= number_format($totalRecords) ?>
                    รายการ
                </p>

            <?php endif; ?>

        </div>
    </div>

</div>

<?php include 'footer.php'; ?>

<script
    src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
></script>

</body>
</html>
