<?php
session_start();

require_once '../config/class.connect.php';

$conn = new connect();

$result = null;
$metrics = null;
$error = null;

$year = $_POST['year'] ?? '2567';
$month = $_POST['month'] ?? '1';
$province = $_POST['province'] ?? '';
$sst = $_POST['sst'] ?? '';
$chl_a = $_POST['chl_a'] ?? '';
$rainfall = $_POST['rainfall'] ?? '';
$wind_speed = $_POST['wind_speed'] ?? '';
$mode = $_POST['mode'] ?? '';

$provinces = [
    1 => 'เพชรบุรี',
    2 => 'สมุทรสงคราม',
    3 => 'สมุทรสาคร',
    4 => 'ชลบุรี',
    5 => 'สมุทรปราการ'
];

$months = [
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

$years = range(2562, 2569);

/*
 * เรียก Python
 * randomforestclassifier.py อยู่ที่:
 * projectA/model/randomforestclassifier.py
 *
 * ถ้าเครื่องใช้คำสั่ง python ไม่ได้ สามารถเปลี่ยนเป็น:
 * $pythonCommand = 'py';
 * หรือใส่ path เต็มของ python.exe
 */
$pythonCommand = 'python';

function runRandomForest($args)
{
    global $pythonCommand;

    $pythonFile = realpath(__DIR__ . '/../model/randomforestclassifier.py');

    if ($pythonFile === false || !file_exists($pythonFile)) {
        throw new Exception(
            'ไม่พบไฟล์ randomforestclassifier.py ที่ projectA/model/'
        );
    }

    $command = escapeshellcmd($pythonCommand)
        . ' ' . escapeshellarg($pythonFile);

    foreach ($args as $arg) {
        $command .= ' ' . escapeshellarg((string)$arg);
    }

    /*
     * 2>&1 ทำให้ PHP ได้ทั้ง stdout/stderr
     */
    $command .= ' 2>&1';

    $output = [];
    $returnCode = 0;

    exec($command, $output, $returnCode);

    $text = trim(implode("\n", $output));

    /*
     * Python ส่ง JSON บรรทัดสุดท้ายออก stdout
     * หา JSON จากบรรทัดท้าย ๆ เพื่อรองรับข้อความจาก Python
     */
    $json = null;

    for ($i = count($output) - 1; $i >= 0; $i--) {
        $line = trim($output[$i]);

        if ($line === '') {
            continue;
        }

        $decoded = json_decode($line, true);

        if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
            $json = $decoded;
            break;
        }
    }

    if ($json === null) {
        throw new Exception(
            "Python ไม่ได้ส่งผลลัพธ์ JSON กลับมา\n\n" . $text
        );
    }

    if ($returnCode !== 0 || !($json['success'] ?? false)) {
        throw new Exception(
            $json['error'] ?? 'เกิดข้อผิดพลาดจาก Random Forest'
        );
    }

    return $json;
}

function loadMetrics()
{
    $metricsFile = realpath(__DIR__ . '/../model/output/classification_metrics.json');

    if ($metricsFile === false || !file_exists($metricsFile)) {
        return null;
    }

    $content = file_get_contents($metricsFile);
    $data = json_decode($content, true);

    return is_array($data) ? $data : null;
}

/*
 * Predict
 */
if ($_SERVER['REQUEST_METHOD'] === 'POST' && in_array($mode, ['predict', 'predict_manual'], true)) {

    try {

        $year = (int)$year;
        $month = (int)$month;
        $province = trim($province);

        if ($year < 2562 || $year > 2569) {
            throw new Exception('ปีต้องอยู่ระหว่าง 2562-2569');
        }

        if ($month < 1 || $month > 12) {
            throw new Exception('เดือนต้องอยู่ระหว่าง 1-12');
        }

        if (!in_array($province, $provinces, true)) {
            throw new Exception('กรุณาเลือกจังหวัดให้ถูกต้อง');
        }

        $args = [
            '--predict',
            '--year',
            $year,
            '--month',
            $month,
            '--province',
            $province
        ];

        /*
         * Manual ใช้เฉพาะ 4 ปัจจัยของโมเดลที่เลือก
         */
        if ($mode === 'predict_manual') {
            $manualValues = [$sst, $chl_a, $rainfall, $wind_speed];
            if (in_array('', $manualValues, true)) {
                throw new Exception('กรุณาระบุค่าทางทะเลและสภาพอากาศให้ครบทั้ง 7 ค่า');
            }
            foreach ($manualValues as $v) {
                if (!is_numeric($v)) {
                    throw new Exception('ค่าปัจจัยสิ่งแวดล้อมทั้งหมดต้องเป็นตัวเลข');
                }
            }
            foreach ([['--sst',$sst],['--chl_a',$chl_a],['--rainfall',$rainfall],
                      ['--wind_speed',$wind_speed]] as $pair) {
                $args[] = $pair[0];
                $args[] = (float)$pair[1];
            }
        }

        $result = runRandomForest($args);

        /*
         * โหลด Accuracy / Precision / Recall / F1 / Confusion Matrix
         */
        $metrics = loadMetrics();

    } catch (Throwable $e) {

        $error = $e->getMessage();

    }
}

/*
 * ถ้ายังไม่มี metrics แต่มี model/output อยู่ ให้โหลดไว้แสดง
 */
if ($metrics === null) {
    $metrics = loadMetrics();
}

$prediction = $result['prediction'] ?? null;
$predictionTh = $result['prediction_th'] ?? null;
$confidence = isset($result['confidence'])
    ? ((float)$result['confidence'] * 100)
    : null;

$probabilities = $result['probabilities'] ?? [];

$input = $result['input'] ?? [];

function levelClass($level)
{
    switch ($level) {
        case 'HIGH':
            return 'level-high';
        case 'MEDIUM':
            return 'level-medium';
        case 'LOW':
            return 'level-low';
        default:
            return '';
    }
}

function featureLabel($feature)
{
    $labels = [
        'month' => 'Month', 'year' => 'Year', 'station_id' => 'Station / Province',
        'sst' => 'Sea Surface Temperature (SST)',
        'chlorophyll_a' => 'Chlorophyll-a',
        'rainfall' => 'Rainfall', 'wind_speed' => 'Wind Speed'
    ];
    return $labels[$feature] ?? $feature;
}

function percent($value)
{
    return number_format(((float)$value) * 100, 1) . '%';
}
?>

<!DOCTYPE html>
<html lang="th">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Random Forest Classification</title>

<link rel="icon" type="image/png" href="../img/logo.png">

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet">

<link rel="stylesheet" href="../css/menu.css">
<link rel="stylesheet" href="../css/data.css">

<style>

.classification-card {
    border-radius: 12px;
}

.card-header {
    font-weight: 600;
}

.predict-result {
    border-radius: 12px;
    padding: 28px;
    text-align: center;
    background: #f8f9fa;
}

.result-level {
    font-size: 48px;
    font-weight: 800;
    letter-spacing: 1px;
}

.level-low {
    color: #dc3545;
}

.level-medium {
    color: #fd7e14;
}

.level-high {
    color: #198754;
}

.confidence-value {
    font-size: 30px;
    font-weight: 700;
}

.probability-bar {
    height: 25px;
}

.metric-box {
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 18px;
    text-align: center;
    height: 100%;
}

.metric-title {
    color: #6c757d;
    font-size: 14px;
}

.metric-value {
    font-size: 26px;
    font-weight: 700;
}

.matrix-table th,
.matrix-table td {
    text-align: center;
    vertical-align: middle;
}

.matrix-table thead th {
    background: #f1f3f5;
}

.info-note {
    font-size: 14px;
    color: #6c757d;
}

.form-section-title {
    font-weight: 600;
    margin-bottom: 16px;
}

.environment-value {
    font-size: 20px;
    font-weight: 600;
}

</style>

</head>

<body>

<?php include 'menu.php'; ?>

<div class="container page-container">

    <!-- Header -->

    <div class="page-header mb-4">

        <h2>
            Random Forest Classification
        </h2>

        <p class="text-muted">
            Mackerel Distribution Level
        </p>

    </div>


    <!-- Error -->

    <?php if ($error !== null): ?>

        <div class="alert alert-danger shadow-sm">
            <strong>เกิดข้อผิดพลาด:</strong>
            <?= htmlspecialchars($error) ?>
        </div>

    <?php endif; ?>


    <!-- Predict from MySQL -->

    <div class="card shadow-sm border-0 mb-4 classification-card">

        <div class="card-header bg-success text-white">

            Predict from Database

        </div>

        <div class="card-body">

            <form method="post">

                <input type="hidden"
                       name="mode"
                       value="predict">

                <div class="row">

                    <!-- Month -->

                    <div class="col-md-4 mb-3">

                        <label class="form-label">
                            Month
                        </label>

                        <select name="month"
                                class="form-select"
                                required>

                            <?php foreach ($months as $m => $monthName): ?>

                                <option value="<?= $m ?>"
                                    <?= ((int)$month === $m)
                                        ? 'selected'
                                        : '' ?>>

                                    <?= htmlspecialchars($monthName) ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>


                    <!-- Year -->

                    <div class="col-md-4 mb-3">

                        <label class="form-label">
                            Year
                        </label>

                        <select name="year"
                                class="form-select"
                                required>

                            <?php foreach ($years as $y): ?>

                                <option value="<?= $y ?>"
                                    <?= ((int)$year === $y)
                                        ? 'selected'
                                        : '' ?>>

                                    <?= $y ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>


                    <!-- Province -->

                    <div class="col-md-4 mb-3">

                        <label class="form-label">
                            Province
                        </label>

                        <select name="province"
                                class="form-select"
                                required>

                            <option value="">
                                -- เลือกจังหวัด --
                            </option>

                            <?php foreach ($provinces as $stationId => $provinceName): ?>

                                <option value="<?= htmlspecialchars($provinceName) ?>"
                                    <?= $province === $provinceName
                                        ? 'selected'
                                        : '' ?>>

                                    <?= htmlspecialchars($provinceName) ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>

                </div>

                <button type="submit"
                        class="btn btn-success">

                    Predict from MySQL

                </button>

            </form>

        </div>

    </div>


    <!-- Manual Parameters -->

    <div class="card shadow-sm border-0 mb-4 classification-card">

        <div class="card-header bg-info text-white">

            Manual Parameters

        </div>

        <div class="card-body">

            <form method="post">

                <input type="hidden"
                       name="mode"
                       value="predict_manual">

                <div class="row">

                    <div class="col-md-3 mb-3">

                        <label class="form-label">
                            Month
                        </label>

                        <select name="month"
                                class="form-select"
                                required>

                            <?php foreach ($months as $m => $monthName): ?>

                                <option value="<?= $m ?>"
                                    <?= ((int)$month === $m)
                                        ? 'selected'
                                        : '' ?>>

                                    <?= htmlspecialchars($monthName) ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>


                    <div class="col-md-3 mb-3">

                        <label class="form-label">
                            Year
                        </label>

                        <select name="year"
                                class="form-select"
                                required>

                            <?php foreach ($years as $y): ?>

                                <option value="<?= $y ?>"
                                    <?= ((int)$year === $y)
                                        ? 'selected'
                                        : '' ?>>

                                    <?= $y ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>


                    <div class="col-md-3 mb-3">

                        <label class="form-label">
                            Province
                        </label>

                        <select name="province"
                                class="form-select"
                                required>

                            <option value="">
                                -- เลือกจังหวัด --
                            </option>

                            <?php foreach ($provinces as $stationId => $provinceName): ?>

                                <option value="<?= htmlspecialchars($provinceName) ?>"
                                    <?= $province === $provinceName
                                        ? 'selected'
                                        : '' ?>>

                                    <?= htmlspecialchars($provinceName) ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>

                </div>

                <div class="row">

                    <div class="col-md-3 mb-3">
                        <label class="form-label">SST (°C)</label>
                        <input type="number" name="sst" class="form-control" step="0.0001" min="-5" max="50" value="<?= htmlspecialchars($sst) ?>" placeholder="เช่น 29.10" required>
                    </div>

                    <div class="col-md-3 mb-3">
                        <label class="form-label">Chlorophyll-a</label>
                        <input type="number" name="chl_a" class="form-control" step="0.0001" min="0" value="<?= htmlspecialchars($chl_a) ?>" placeholder="เช่น 2.40" required>
                    </div>

                    <div class="col-md-3 mb-3">
                        <label class="form-label">Rainfall</label>
                        <input type="number" name="rainfall" class="form-control" step="0.0001" min="0" value="<?= htmlspecialchars($rainfall) ?>" placeholder="เช่น 20.5" required>
                    </div>

                    <div class="col-md-3 mb-3">
                        <label class="form-label">Wind Speed</label>
                        <input type="number" name="wind_speed" class="form-control" step="0.0001" min="0" value="<?= htmlspecialchars($wind_speed) ?>" placeholder="เช่น 16.19" required>
                    </div>

                </div>

                <button type="submit"
                        class="btn btn-info text-white">

                    Predict from Manual Value

                </button>

            </form>

        </div>

    </div>


    <!-- Prediction Result -->

    <?php if ($result !== null): ?>

    <div class="card shadow-sm border-0 mb-4 classification-card">

        <div class="card-header">

            Prediction Result

        </div>

        <div class="card-body">

            <div class="alert alert-light border mb-4">
                <strong>Prediction Mode:</strong>
                <?= ($result['mode'] ?? '') === 'manual' ? 'Manual Parameters' : 'MySQL Parameters' ?>
            </div>

            <div class="predict-result mb-4">

                <div class="text-muted mb-2">
                    ระดับปริมาณปลาทูที่คาดการณ์
                </div>

                <div class="result-level <?= levelClass($prediction) ?>">

                    <?= htmlspecialchars($prediction) ?>

                </div>

                <div class="mt-2">

                    <?= htmlspecialchars($predictionTh) ?>

                </div>

                <?php if ($confidence !== null): ?>

                    <hr>

                    <div class="text-muted">
                        Prediction Confidence
                    </div>

                    <div class="confidence-value">
                        <?= number_format($confidence, 1) ?>%
                    </div>

                <?php endif; ?>

            </div>


            <!-- Input Summary -->

            <h5 class="form-section-title">
                Input Parameters
            </h5>

            <div class="row mb-4">

                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Year
                        </div>

                        <div class="metric-value">
                            <?= htmlspecialchars($input['year'] ?? '-') ?>
                        </div>

                    </div>

                </div>


                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Month
                        </div>

                        <div class="metric-value">

                            <?php
                            $resultMonth = (int)($input['month'] ?? 0);
                            echo htmlspecialchars(
                                $months[$resultMonth] ?? '-'
                            );
                            ?>

                        </div>

                    </div>

                </div>


                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Province
                        </div>

                        <div class="metric-value">

                            <?= htmlspecialchars(
                                $input['province'] ?? '-'
                            ) ?>

                        </div>

                    </div>

                </div>


                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Station ID
                        </div>

                        <div class="metric-value">

                            <?= htmlspecialchars(
                                $input['station_id'] ?? '-'
                            ) ?>

                        </div>

                    </div>

                </div>

            </div>


            <!-- Environment -->

            <h5 class="form-section-title">
                Environmental Parameters
            </h5>

            <div class="row mb-4">

                <div class="col-md-6 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Sea Surface Temperature (SST)
                        </div>

                        <div class="environment-value">

                            <?= isset($input['sst'])
                                ? number_format(
                                    (float)$input['sst'],
                                    4
                                ) . ' °C'
                                : '-' ?>

                        </div>

                    </div>

                </div>


                <div class="col-md-6 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Chlorophyll-a
                        </div>

                        <div class="environment-value">

                            <?= isset($input['chlorophyll_a'])
                                ? number_format(
                                    (float)$input['chlorophyll_a'],
                                    4
                                )
                                : '-' ?>

                        </div>

                    </div>

                </div>

            </div>


            <!-- Weather -->
            <h5 class="form-section-title">
                Weather Parameters
            </h5>

            <div class="row mb-4">
                <div class="col-md-6 mb-3">
                    <div class="metric-box">
                        <div class="metric-title">
                            Rainfall
                        </div>
                        <div class="environment-value">
                            <?= isset($input['rainfall'])
                                ? number_format((float)$input['rainfall'], 4) . ' mm'
                                : '-' ?>
                        </div>
                    </div>
                </div>

                <div class="col-md-6 mb-3">
                    <div class="metric-box">
                        <div class="metric-title">
                            Wind Speed
                        </div>
                        <div class="environment-value">
                            <?= isset($input['wind_speed'])
                                ? number_format((float)$input['wind_speed'], 4) . ' m/s'
                                : '-' ?>
                        </div>
                    </div>
                </div>

            </div>

            <!-- Probability -->

            <h5 class="form-section-title">
                Class Probability
            </h5>

            <div class="row">

                <?php foreach (['LOW', 'MEDIUM', 'HIGH'] as $level): ?>

                    <div class="col-md-4 mb-3">

                        <div class="metric-box">

                            <div class="metric-title">
                                <?= $level ?>
                            </div>

                            <div class="metric-value
                                <?= levelClass($level) ?>">

                                <?= isset($probabilities[$level])
                                    ? number_format(
                                        $probabilities[$level] * 100,
                                        1
                                    ) . '%'
                                    : '0.0%' ?>

                            </div>

                            <div class="progress probability-bar mt-2">

                                <div class="progress-bar"
                                     role="progressbar"
                                     style="width:
                                     <?= isset($probabilities[$level])
                                         ? $probabilities[$level] * 100
                                         : 0 ?>%">

                                </div>

                            </div>

                        </div>

                    </div>

                <?php endforeach; ?>

            </div>

            <div class="alert alert-warning mt-4 mb-0">

                <strong>หมายเหตุ:</strong> LOW / MEDIUM / HIGH คือระดับปริมาณปลาทูที่โมเดลคาดการณ์
                โดยเรียนรู้จากข้อมูลปริมาณปลาทูขึ้นท่าย้อนหลัง ไม่ใช่จำนวนปลาจริง ณ เวลาปัจจุบัน
                และไม่ใช่ผลยืนยันพื้นที่หรือช่วงวางไข่

            </div>

        </div>

    </div>

    <?php endif; ?>


    <!-- Model Evaluation -->

    <?php if ($metrics !== null): ?>

    <div class="card shadow-sm border-0 mb-4 classification-card">

        <div class="card-header bg-primary text-white">

            Model Evaluation

        </div>

        <div class="card-body">

            <p class="info-note">

                Training:
                <?= htmlspecialchars(
                    implode(
                        ', ',
                        $metrics['train']['years'] ?? []
                    )
                ) ?>

                &nbsp;|&nbsp;

                Test:
                <?= htmlspecialchars(
                    (string)($metrics['test']['year'] ?? '-')
                ) ?>

                &nbsp;|&nbsp;

                Test Rows:
                <?= htmlspecialchars(
                    (string)($metrics['test']['rows'] ?? '-')
                ) ?>

            </p>


            <!-- Metrics -->

            <div class="row mb-4">

                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Accuracy
                        </div>

                        <div class="metric-value">

                            <?= percent(
                                $metrics['accuracy'] ?? 0
                            ) ?>

                        </div>

                    </div>

                </div>


                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Macro Precision
                        </div>

                        <div class="metric-value">

                            <?= percent(
                                $metrics['precision_macro'] ?? 0
                            ) ?>

                        </div>

                    </div>

                </div>


                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Macro Recall
                        </div>

                        <div class="metric-value">

                            <?= percent(
                                $metrics['recall_macro'] ?? 0
                            ) ?>

                        </div>

                    </div>

                </div>


                <div class="col-md-3 mb-3">

                    <div class="metric-box">

                        <div class="metric-title">
                            Macro F1-score
                        </div>

                        <div class="metric-value">

                            <?= percent(
                                $metrics['f1_macro'] ?? 0
                            ) ?>

                        </div>

                    </div>

                </div>

            </div>


            <!-- Confusion Matrix -->

            <h5 class="form-section-title">
                Confusion Matrix
            </h5>

            <?php
            $cm = $metrics['confusion_matrix']['matrix'] ?? [];
            $cmLabels = $metrics['confusion_matrix']['labels']
                ?? ['LOW', 'MEDIUM', 'HIGH'];
            ?>

            <div class="table-responsive">

                <table class="table table-bordered matrix-table">

                    <thead>

                        <tr>

                            <th rowspan="2">
                                Actual \ Predicted
                            </th>

                            <?php foreach ($cmLabels as $label): ?>

                                <th>
                                    <?= htmlspecialchars($label) ?>
                                </th>

                            <?php endforeach; ?>

                        </tr>

                    </thead>

                    <tbody>

                        <?php foreach ($cmLabels as $i => $actual): ?>

                            <tr>

                                <th>
                                    <?= htmlspecialchars($actual) ?>
                                </th>

                                <?php foreach ($cmLabels as $j => $predicted): ?>

                                    <td>

                                        <?= htmlspecialchars(
                                            (string)(
                                                $cm[$i][$j] ?? 0
                                            )
                                        ) ?>

                                    </td>

                                <?php endforeach; ?>

                            </tr>

                        <?php endforeach; ?>

                    </tbody>

                </table>

            </div>


            <!-- Feature Importance -->

            <?php if (!empty($metrics['feature_importance'])): ?>

                <h5 class="form-section-title mt-4">
                    Feature Importance
                </h5>

                <div class="table-responsive">

                    <table class="table table-bordered">

                        <thead>

                            <tr>
                                <th>Feature</th>
                                <th>Importance</th>
                            </tr>

                        </thead>

                        <tbody>

                            <?php
                            $featureImportance =
                                $metrics['feature_importance'];

                            arsort($featureImportance);
                            ?>

                            <?php foreach (
                                $featureImportance
                                as $feature => $importance
                            ): ?>

                                <tr>

                                    <td>
                                        <?= htmlspecialchars(featureLabel($feature)) ?>
                                    </td>

                                    <td>
                                        <?= number_format(
                                            (float)$importance * 100,
                                            2
                                        ) ?>%
                                    </td>

                                </tr>

                            <?php endforeach; ?>

                        </tbody>

                    </table>

                </div>

            <?php endif; ?>


            <!-- Target Definition -->

            <?php
            $targetDefinition =
                $metrics['target_definition'] ?? null;
            ?>

            <?php if ($targetDefinition): ?>

                <div class="alert alert-secondary mt-4 mb-0">

                    <strong>เกณฑ์แบ่งระดับ Target จากข้อมูล Training:</strong>

                    ใช้เปอร์เซ็นไทล์ที่ 33 และ 66 ของปริมาณปลาทูรวมรายจังหวัด/เดือน
                    โดยคำนวณจากชุด Training ปี 2562–2566 เท่านั้น เพื่อลด Data Leakage

                    <br>

                    LOW:
                    <?= htmlspecialchars(
                        $targetDefinition['definition']['LOW']
                        ?? '-'
                    ) ?>

                    <br>

                    MEDIUM:
                    <?= htmlspecialchars(
                        $targetDefinition['definition']['MEDIUM']
                        ?? '-'
                    ) ?>

                    <br>

                    HIGH:
                    <?= htmlspecialchars(
                        $targetDefinition['definition']['HIGH']
                        ?? '-'
                    ) ?>

                </div>

            <?php endif; ?>

        </div>

    </div>

    <?php else: ?>

    <div class="card shadow-sm border-0 mb-4">

        <div class="card-header">
            Model Evaluation
        </div>

        <div class="card-body">

            <div class="alert alert-secondary mb-0">

                ยังไม่พบผลประเมินโมเดล กรุณา Train โมเดลด้วยไฟล์
                randomforestclassifier.py ก่อนใช้งาน หากยังไม่มีโมเดล ระบบจะ Train อัตโนมัติเมื่อทำนายครั้งแรก

            </div>

        </div>

    </div>

    <?php endif; ?>


    <!-- Model Information -->

    <div class="card shadow-sm border-0 mb-4">

        <div class="card-header">
            Model Information
        </div>

        <div class="card-body">


            <div class="row">
                <div class="col-md-6 mb-3">
                    <h6>Model and Target</h6>
                    <ul class="mb-0">
                        <li>Algorithm: Random Forest Classification</li>
                        <li>Target: LOW / MEDIUM / HIGH</li>
                        <li>Threshold: 33rd / 66th percentile ของปริมาณปลาใน Training set</li>
                        <li>Training data: ปี 2562–2566</li>
                        <li>Testing data: ปี 2567</li>
                    </ul>
                </div>

                <div class="col-md-6 mb-3">
                    <h6>Input Features</h6>
                    <ul class="mb-0">
                        <li>เวลาและพื้นที่: Month, Year, Station / Province</li>
                        <li>ข้อมูลทางทะเล: SST และ Chlorophyll-a</li>
                        <li>ข้อมูลอากาศ: Rainfall และ Wind Speed</li>
                    </ul>
                </div>
            </div>

            <div class="alert alert-light border mt-3 mb-0">
                <strong>Prediction modes:</strong>
                Database Parameters ดึงค่าทั้งหมดจากฐานข้อมูลตามเดือน ปี และจังหวัด ส่วน Manual Parameters
                ให้ผู้ใช้กรอกเอง
            </div>

        </div>

    </div>

</div>

<?php include 'footer.php'; ?>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js">
</script>

</body>

</html>