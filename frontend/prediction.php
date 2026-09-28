<?php

session_start();

$conn = new mysqli(
    "127.0.0.1",
    "root",
    "",
    "projecta"
);

if ($conn->connect_error) {
    die(
        "เชื่อมต่อฐานข้อมูลไม่ได้: "
        . $conn->connect_error
    );
}

$conn->set_charset("utf8mb4");


/* =========================================================
   PYTHON
========================================================= */

$python = "python";


/* =========================================================
   MONTHS
========================================================= */

$months = [
    1  => "มกราคม",
    2  => "กุมภาพันธ์",
    3  => "มีนาคม",
    4  => "เมษายน",
    5  => "พฤษภาคม",
    6  => "มิถุนายน",
    7  => "กรกฎาคม",
    8  => "สิงหาคม",
    9  => "กันยายน",
    10 => "ตุลาคม",
    11 => "พฤศจิกายน",
    12 => "ธันวาคม"
];


/* =========================================================
   PROVINCES
========================================================= */

$provinces = [
    1 => "เพชรบุรี",
    2 => "สมุทรสงคราม",
    3 => "สมุทรสาคร",
    4 => "ชลบุรี",
    5 => "สมุทรปราการ"
];


/* =========================================================
   PARAMETERS
========================================================= */

$selectedMonth =
    isset($_POST["month"])
    ? intval($_POST["month"])
    : 1;

$selectedYear =
    isset($_POST["year"])
    ? intval($_POST["year"])
    : 2567;

$selectedProvince =
    isset($_POST["province"])
    ? trim($_POST["province"])
    : "สมุทรสงคราม";


/* =========================================================
   RESULTS
========================================================= */

$regression = null;
$classify = null;
$cluster = null;

$mapData = [];

$error = null;

$spawning = false;
$spawningDescription = "";


/* =========================================================
   GET STATION ID
========================================================= */

function getStationId(
    $province,
    $provinces
) {

    foreach (
        $provinces
        as $stationId => $name
    ) {

        if ($name === $province) {
            return $stationId;
        }
    }

    return null;
}


/* =========================================================
   RUN PYTHON JSON
========================================================= */

function runPythonJson(
    $python,
    $pythonFile,
    $args
) {

    if (
        $pythonFile === false
        ||
        !file_exists($pythonFile)
    ) {

        throw new Exception(
            "ไม่พบไฟล์ Python: "
            . $pythonFile
        );
    }


    /*
     * Python command
     */
    $command =
        escapeshellarg(
            $python
        )
        . " "
        .
        escapeshellarg(
            $pythonFile
        );


    /*
     * Arguments
     */
    foreach (
        $args as $arg
    ) {

        $command .=
            " "
            .
            escapeshellarg(
                (string)$arg
            );
    }


    /*
     * stderr -> stdout
     */
    $command .= " 2>&1";


    $output = [];

    $returnCode = 0;


    /*
     * Run Python
     */
    exec(
        $command,
        $output,
        $returnCode
    );


    /*
     * Raw output
     */
    $text =
        trim(
            implode(
                "\n",
                $output
            )
        );


    $json = null;


    /*
     * หา JSON จาก output
     */
    for (
        $i = count($output) - 1;
        $i >= 0;
        $i--
    ) {

        $line =
            trim(
                $output[$i]
            );


        if ($line === "") {
            continue;
        }


        $decoded =
            json_decode(
                $line,
                true
            );


        if (
            json_last_error()
            === JSON_ERROR_NONE
            &&
            is_array($decoded)
        ) {

            $json = $decoded;

            break;
        }
    }


    /*
     * ไม่มี JSON
     */
    if ($json === null) {

        throw new Exception(
            "Python ไม่ได้ส่ง JSON กลับมา\n\n"
            . "Python Output:\n"
            . $text
        );
    }


    /*
     * Python error
     */
    if (
        $returnCode !== 0
        &&
        ($json["status"] ?? "")
        !== "success"
    ) {

        throw new Exception(
            $json["message"]
            ??
            $json["error"]
            ??
            "Python ทำงานไม่สำเร็จ"
        );
    }


    return $json;
}


/* =========================================================
   RUN PREDICTION
========================================================= */

if (
    $_SERVER["REQUEST_METHOD"] === "POST"
    &&
    isset($_POST["run_prediction"])
) {

    try {

        /* =================================================
           VALIDATE MONTH
        ================================================= */

        if (
            $selectedMonth < 1
            ||
            $selectedMonth > 12
        ) {

            throw new Exception(
                "เดือนต้องอยู่ระหว่าง 1-12"
            );
        }


        /* =================================================
           VALIDATE YEAR
        ================================================= */

        if (
            $selectedYear < 2562
            ||
            $selectedYear > 2569
        ) {

            throw new Exception(
                "ปีต้องอยู่ระหว่าง 2562-2569"
            );
        }


        /* =================================================
           STATION
        ================================================= */

        $stationId =
            getStationId(
                $selectedProvince,
                $provinces
            );


        if (
            $stationId === null
        ) {

            throw new Exception(
                "ไม่พบจังหวัดที่เลือก"
            );
        }


        /* =================================================
           1. REGRESSION
        ================================================= */

        $regressionFile =
            __DIR__
            . DIRECTORY_SEPARATOR
            . ".."
            . DIRECTORY_SEPARATOR
            . "model"
            . DIRECTORY_SEPARATOR
            . "Regression_Linear.py";


        if (
            file_exists(
                $regressionFile
            )
        ) {

            /*
             * จังหวัด Base64
             */
            $provinceB64 =
                base64_encode(
                    $selectedProvince
                );


            try {

                /*
                 * Python:
                 *
                 * province
                 * year
                 * month
                 * --b64
                 */

                $regression =
                    runPythonJson(

                        $python,

                        $regressionFile,

                        [
                            $provinceB64,
                            $selectedYear,
                            $selectedMonth,
                            "--b64"
                        ]
                    );

            }
            catch (Throwable $e) {

                $regression = [

                    "status" =>
                        "error",

                    "message" =>
                        $e->getMessage()

                ];
            }

        }
        else {

            $regression = [

                "status" =>
                    "error",

                "message" =>
                    "ไม่พบไฟล์ Regression_Linear.py\n"
                    .
                    $regressionFile

            ];
        }


        /* =================================================
           2. RANDOM FOREST
        ================================================= */

        $rfFile =
            __DIR__
            . DIRECTORY_SEPARATOR
            . ".."
            . DIRECTORY_SEPARATOR
            . "model"
            . DIRECTORY_SEPARATOR
            . "randomforestclassifier.py";


        if (
            file_exists(
                $rfFile
            )
        ) {

            try {

                $classify =
                    runPythonJson(

                        $python,

                        $rfFile,

                        [
                            "--predict",
                            "--year",
                            $selectedYear,
                            "--month",
                            $selectedMonth,
                            "--province",
                            $selectedProvince
                        ]
                    );

            }
            catch (Throwable $e) {

                $classify = [

                    "success" =>
                        false,

                    "error" =>
                        $e->getMessage()

                ];
            }

        }
        else {

            $classify = [

                "success" =>
                    false,

                "error" =>
                    "ไม่พบไฟล์ randomforestclassifier.py"

            ];
        }


        /* =================================================
           3. K-MEANS
        ================================================= */

        $clusterSql = "

            SELECT
                ROUND(
                    AVG(cluster)
                ) AS cluster

            FROM dataset_ml

            WHERE station_id = $stationId

              AND year = $selectedYear

              AND month = $selectedMonth

        ";


        $clusterResult =
            $conn->query(
                $clusterSql
            );


        if (
            $clusterResult
            &&
            $clusterRow =
            $clusterResult->fetch_assoc()
        ) {

            if (
                $clusterRow["cluster"]
                !== null
            ) {

                $cluster =
                    intval(
                        $clusterRow["cluster"]
                    );
            }
        }


/* =================================================
   4. SPAWNING
================================================= */

$spawning = false;

$spawningDescription = "";


/*
 * ตรวจจากฐานข้อมูลก่อน
 */
$spawnSql = "

    SELECT

        start_month,
        end_month,
        start_day,
        end_day,
        description

    FROM spawning_season

    WHERE

        start_month <= $selectedMonth

        AND

        end_month >= $selectedMonth

    LIMIT 1

";


$spawnResult =
    $conn->query(
        $spawnSql
    );


/*
 * ถ้ามีข้อมูลในฐานข้อมูล
 */
if (
    $spawnResult
    &&
    $spawnResult->num_rows > 0
) {

    $spawnRow =
        $spawnResult->fetch_assoc();


    $spawning = true;


    $spawningDescription =
        !empty(
            $spawnRow["description"]
        )
        ?
        $spawnRow["description"]
        :
        "อยู่ในช่วงฤดูวางไข่ของปลาทู";

}


/*
 * ถ้าไม่มีข้อมูลใน spawning_season
 * ให้ใช้ช่วงฤดูวางไข่สำรอง
 * มิถุนายน - สิงหาคม
 */
else {

    if (
        $selectedMonth >= 6
        &&
        $selectedMonth <= 8
    ) {

        $spawning = true;

        $spawningDescription =
            "ช่วงฤดูวางไข่ของปลาทู "
            . "ระหว่างเดือนมิถุนายน - สิงหาคม";

    }

}


        /* =================================================
           5. HEATMAP
        ================================================= */

        $mapSql = "

            SELECT

                s.station_name,

                s.latitude,

                s.longitude,

                d.station_id,

                d.year,

                d.month,

                SUM(
                    d.amount
                ) AS amount,

                ROUND(
                    AVG(d.cluster)
                ) AS cluster

            FROM dataset_ml d

            INNER JOIN station s

                ON d.station_id = s.id

            WHERE

                d.year = $selectedYear

                AND

                d.month = $selectedMonth

            GROUP BY

                s.station_name,

                s.latitude,

                s.longitude,

                d.station_id,

                d.year,

                d.month

            ORDER BY
                d.station_id

        ";


        $mapResult =
            $conn->query(
                $mapSql
            );


        if ($mapResult) {

            while (
                $row =
                $mapResult->fetch_assoc()
            ) {

                if (
                    floatval(
                        $row["latitude"]
                    ) != 0
                    &&
                    floatval(
                        $row["longitude"]
                    ) != 0
                ) {

                    $mapData[] =
                        $row;
                }
            }
        }

    }
    catch (Throwable $e) {

        $error =
            $e->getMessage();
    }
}


/* =========================================================
   REGRESSION DISPLAY
========================================================= */

$regressionTon = null;


/*
 * รับ ton โดยตรง
 */
if (
    is_array($regression)
    &&
    isset(
        $regression["ton"]
    )
    &&
    is_numeric(
        $regression["ton"]
    )
) {

    $regressionTon =
        floatval(
            $regression["ton"]
        );
}


/* =========================================================
   CLASSIFICATION DISPLAY
========================================================= */

$classLevel = null;
$classThai = null;
$classConfidence = null;


if (
    is_array($classify)
) {

    $classLevel =
        $classify["prediction"]
        ??
        null;


    $classThai =
        $classify["prediction_th"]
        ??
        null;


    if (
        isset(
            $classify["confidence"]
        )
    ) {

        $classConfidence =
            floatval(
                $classify["confidence"]
            );


        if (
            $classConfidence <= 1
        ) {

            $classConfidence *= 100;
        }
    }
}


$conn->close();

?>

<!DOCTYPE html>

<html lang="th">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Prediction</title>

<link
    rel="icon"
    type="image/png"
    href="../img/logo.png"
>

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

<link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
>

<script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
></script>


<style>

.result-card {
    min-height: 180px;
}

.result-value {
    font-size: 32px;
    font-weight: 700;
}

.spawning-alert {
    background: #fff3cd;
    border: 1px solid #ffecb5;
    color: #664d03;
    padding: 15px 20px;
    border-radius: 10px;
    margin-bottom: 24px;
}

.spawning-normal {
    background: #d1e7dd;
    border-color: #badbcc;
    color: #0f5132;
}

#prediction-map {
    height: 500px;
    width: 100%;
    border-radius: 8px;
}

.cluster-badge {
    font-size: 18px;
    padding: 10px 18px;
}

.error-box {
    white-space: pre-wrap;
}

</style>

</head>


<body>


<?php include 'menu.php'; ?>


<div class="container page-container">


    <!-- =====================================================
         HEADER
    ====================================================== -->

    <div class="page-header mb-4">

        <h2>
            Prediction Dashboard
        </h2>

        <p class="text-muted">
            Integrated AI Prediction System
        </p>

    </div>


    <!-- =====================================================
         GLOBAL ERROR
    ====================================================== -->

    <?php if (
        $error !== null
    ): ?>

        <div
            class="alert
                   alert-danger
                   error-box"
        >

            <strong>
                เกิดข้อผิดพลาด:
            </strong>

            <?= htmlspecialchars(
                $error
            ) ?>

        </div>

    <?php endif; ?>


    <!-- =====================================================
         PARAMETERS
    ====================================================== -->

    <div
        class="card
               shadow-sm
               border-0
               mb-4"
    >

        <div
            class="card-header"
        >

            Prediction Parameters

        </div>


        <div
            class="card-body"
        >

            <form
                method="post"
            >

                <div class="row">


                    <!-- MONTH -->

                    <div
                        class="col-md-4
                               mb-3"
                    >

                        <label class="form-label">

                            Month

                        </label>


                        <select
                            class="form-select"
                            name="month"
                            required
                        >

                            <?php foreach (
                                $months
                                as $num => $name
                            ): ?>

                                <option
                                    value="<?= $num ?>"
                                    <?= (
                                        $selectedMonth
                                        == $num
                                    )
                                    ? "selected"
                                    : ""
                                    ?>
                                >

                                    <?= $name ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>


                    <!-- YEAR -->

                    <div
                        class="col-md-4
                               mb-3"
                    >

                        <label
                            class="form-label"
                        >

                            Year

                        </label>


                        <select
                            class="form-select"
                            name="year"
                            required
                        >

                            <?php

                            for (
                                $y = 2562;
                                $y <= 2569;
                                $y++
                            ):

                            ?>

                                <option
                                    value="<?= $y ?>"
                                    <?= (
                                        $selectedYear
                                        == $y
                                    )
                                    ? "selected"
                                    : ""
                                    ?>
                                >

                                    <?= $y ?>

                                </option>

                            <?php endfor; ?>

                        </select>

                    </div>


                    <!-- PROVINCE -->

                    <div
                        class="col-md-4
                               mb-3"
                    >

                        <label
                            class="form-label"
                        >

                            Province

                        </label>


                        <select
                            class="form-select"
                            name="province"
                            required
                        >

                            <?php foreach (
                                $provinces
                                as $id => $name
                            ): ?>

                                <option
                                    value="<?= htmlspecialchars(
                                        $name
                                    ) ?>"
                                    <?= (
                                        $selectedProvince
                                        === $name
                                    )
                                    ? "selected"
                                    : ""
                                    ?>
                                >

                                    <?= htmlspecialchars(
                                        $name
                                    ) ?>

                                </option>

                            <?php endforeach; ?>

                        </select>

                    </div>

                </div>


                <button
                    type="submit"
                    name="run_prediction"
                    class="btn btn-primary"
                >

                    Predict

                </button>

            </form>

        </div>

    </div>


    <!-- =====================================================
         SPAWNING ALERT
    ====================================================== -->

    <?php if (
        isset(
            $_POST["run_prediction"]
        )
    ): ?>


        <?php if (
            $spawning
        ): ?>

            <div
                class="spawning-alert"
            >

                ⚠️

                <strong>
                    แจ้งเตือน:
                </strong>

                เดือน

                <?= htmlspecialchars(
                    $months[
                        $selectedMonth
                    ]
                ) ?>

                อยู่ในช่วงฤดูวางไข่ของปลาทู


                <?php if (
                    !empty(
                        $spawningDescription
                    )
                ): ?>

                    <br>

                    <small>

                        <?= htmlspecialchars(
                            $spawningDescription
                        ) ?>

                    </small>

                <?php endif; ?>

            </div>


        <?php else: ?>

            <div
                class="
                    spawning-alert
                    spawning-normal
                "
            >

                ☑️

                เดือน

                <?= htmlspecialchars(
                    $months[
                        $selectedMonth
                    ]
                ) ?>

                ไม่อยู่ในช่วงฤดูวางไข่ของปลาทู

            </div>

        <?php endif; ?>

    <?php endif; ?>


    <!-- =====================================================
         RESULT CARDS
    ====================================================== -->

    <div
        class="row mb-4"
    >


        <!-- REGRESSION -->

        <div
            class="col-md-4
                   mb-3"
        >

            <div
                class="
                    card
                    shadow-sm
                    result-card
                "
            >

                <div
                    class="card-body"
                >

                    <h5>
                        Regression
                    </h5>


                    <?php if (
                        $regressionTon !== null
                    ): ?>

                        <div
                            class="
                                result-value
                                text-primary
                            "
                        >

                            <?= number_format(
                                $regressionTon,
                                2
                            ) ?>

                        </div>

                        <small>
                            Ton
                        </small>


                    <?php else: ?>

                        <div
                            class="result-value"
                        >

                            -

                        </div>

                        <small>
                            Ton
                        </small>

                    <?php endif; ?>

                </div>

            </div>

        </div>


        <!-- CLASSIFICATION -->

        <div
            class="col-md-4
                   mb-3"
        >

            <div
                class="
                    card
                    shadow-sm
                    result-card
                "
            >

                <div
                    class="card-body"
                >

                    <h5>
                        Classification
                    </h5>


                    <?php if (
                        $classLevel !== null
                    ): ?>


                        <?php

                        if (
                            $classLevel
                            === "LOW"
                        ) {

                            $badgeClass =
                                "bg-danger";

                        }
                        elseif (
                            $classLevel
                            === "MEDIUM"
                        ) {

                            $badgeClass =
                                "bg-warning text-dark";

                        }
                        elseif (
                            $classLevel
                            === "HIGH"
                        ) {

                            $badgeClass =
                                "bg-success";

                        }
                        else {

                            $badgeClass =
                                "bg-secondary";

                        }

                        ?>


                        <span
                            class="
                                badge
                                <?= $badgeClass ?>
                                fs-5
                                px-4
                                py-2
                            "
                        >

                            <?= htmlspecialchars(
                                $classLevel
                            ) ?>

                        </span>


                        <?php if (
                            $classThai !== null
                        ): ?>

                            <div
                                class="mt-2"
                            >

                                <?= htmlspecialchars(
                                    $classThai
                                ) ?>

                            </div>

                        <?php endif; ?>


                        <?php if (
                            $classConfidence
                            !== null
                        ): ?>

                            <small
                                class="
                                    d-block
                                    mt-2
                                "
                            >

                                Confidence:

                                <?= number_format(
                                    $classConfidence,
                                    1
                                ) ?>%

                            </small>

                        <?php endif; ?>


                    <?php else: ?>

                        <span
                            class="
                                badge
                                bg-secondary
                                fs-5
                                px-4
                                py-2
                            "
                        >

                            -

                        </span>

                    <?php endif; ?>


                    <small
                        class="
                            d-block
                            mt-2
                        "
                    >

                        Density Level

                    </small>

                </div>

            </div>

        </div>


        <!-- K-MEANS -->

        <div
            class="col-md-4
                   mb-3"
        >

            <div
                class="
                    card
                    shadow-sm
                    result-card
                "
            >

                <div
                    class="card-body"
                >

                    <h5>
                        Cluster
                    </h5>


                    <?php if (
                        $cluster !== null
                    ): ?>

                        <span
                            class="
                                badge
                                bg-primary
                                cluster-badge
                            "
                        >

                            กลุ่มที่
                            <?= $cluster + 1 ?>

                        </span>

                    <?php else: ?>

                        <div
                            class="result-value"
                        >

                            -

                        </div>

                    <?php endif; ?>


                    <small
                        class="
                            d-block
                            mt-2
                        "
                    >

                        K-Means Cluster Group

                    </small>

                </div>

            </div>

        </div>

    </div>


    <!-- =====================================================
         HEATMAP
    ====================================================== -->

    <div
        class="
            card
            shadow-sm
            border-0
            mb-4
        "
    >

        <div
            class="card-header"
        >

            Heatmap

        </div>


        <div
            class="card-body"
        >

            <div
                id="prediction-map"
            ></div>

        </div>

    </div>


    <!-- =====================================================
         AI SUMMARY
    ====================================================== -->

    <div
        class="
            card
            shadow-sm
            border-0
            mb-5
        "
    >

        <div
            class="card-header"
        >

            AI Summary

        </div>


        <div
            class="card-body"
        >


            <?php if (
                $regressionTon !== null
                ||
                $classLevel !== null
                ||
                $cluster !== null
            ): ?>


                <p>

                    จังหวัด

                    <strong>

                        <?= htmlspecialchars(
                            $selectedProvince
                        ) ?>

                    </strong>

                    เดือน

                    <strong>

                        <?= htmlspecialchars(
                            $months[
                                $selectedMonth
                            ]
                        ) ?>

                    </strong>

                    ปี

                    <strong>

                        <?= $selectedYear ?>

                    </strong>

                </p>


                <?php if (
                    $regressionTon !== null
                ): ?>

                    <p>

                        Regression
                        คาดการณ์ปริมาณปลาทูประมาณ

                        <strong
                            class="text-primary"
                        >

                            <?= number_format(
                                $regressionTon,
                                2
                            ) ?>

                            ตัน

                        </strong>

                    </p>

                <?php endif; ?>


                <?php if (
                    $classLevel !== null
                ): ?>

                    <p>

                        Random Forest
                        จัดระดับเป็น

                        <strong>

                            <?= htmlspecialchars(
                                $classLevel
                            ) ?>

                        </strong>


                        <?php if (
                            $classThai !== null
                        ): ?>

                            (
                            <?= htmlspecialchars(
                                $classThai
                            ) ?>
                            )

                        <?php endif; ?>

                    </p>

                <?php endif; ?>


                <?php if (
                    $cluster !== null
                ): ?>

                    <p>

                        K-Means
                        จัดให้อยู่ใน

                        <strong>

                            กลุ่มที่
                            <?= $cluster + 1 ?>

                        </strong>

                    </p>

                <?php endif; ?>


            <?php else: ?>

                <p
                    class="text-muted mb-0"
                >

                    เลือกเดือน ปี และจังหวัด
                    จากนั้นกด Predict
                    เพื่อให้ระบบประมวลผล

                </p>

            <?php endif; ?>

        </div>

    </div>


</div>


<!-- =======================================================
     LEAFLET
======================================================= -->

<script>

var map =
    L.map(
        "prediction-map"
    ).setView(
        [13.25, 100.15],
        8
    );


L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 18,
        attribution:
            "&copy; OpenStreetMap"
    }
).addTo(map);


var mapData =
    <?= json_encode(
        $mapData,
        JSON_UNESCAPED_UNICODE
        |
        JSON_UNESCAPED_SLASHES
    ) ?>;


mapData.forEach(
    function(row) {

        var lat =
            parseFloat(
                row.latitude
            );

        var lng =
            parseFloat(
                row.longitude
            );

        var amount =
            parseFloat(
                row.amount
            );


        if (
            !isFinite(lat)
            ||
            !isFinite(lng)
        ) {

            return;
        }


        var clusterValue =
            parseInt(
                row.cluster
            );


        var color =
            clusterValue === 0
            ? "red"
            : "blue";


        var radius = 6;


        if (
            amount >= 100
        ) {

            radius = 18;

        }
        else if (
            amount >= 50
        ) {

            radius = 14;

        }
        else if (
            amount >= 10
        ) {

            radius = 10;

        }


        L.circleMarker(
            [lat, lng],
            {
                radius: radius,
                color: color,
                fillColor: color,
                fillOpacity: 0.8
            }
        )
        .addTo(map)
        .bindPopup(

            "<b>"
            +
            row.station_name
            +
            "</b><br>"
            +

            "ปี : "
            +
            row.year
            +
            "<br>"
            +

            "เดือน : "
            +
            row.month
            +
            "<br>"
            +

            "<b>ปริมาณปลา :</b> "
            +
            amount.toFixed(2)
            +
            " ตัน<br>"
            +

            "<b>Cluster :</b> "
            +
            (
                isNaN(
                    clusterValue
                )
                ? "N/A"
                :
                "กลุ่มที่ "
                +
                (
                    clusterValue + 1
                )
            )

        );

    }
);


/* =========================================================
   MAP LEGEND
========================================================= */

var legend =
    L.control({
        position:
            "bottomright"
    });


legend.onAdd =
function() {

    var div =
        L.DomUtil.create(
            "div",
            "legend"
        );


    div.style.background =
        "white";

    div.style.padding =
        "10px";

    div.style.borderRadius =
        "8px";

    div.style.boxShadow =
        "0 0 10px rgba(0,0,0,0.2)";


    div.innerHTML =

        "<b>K-Means</b><br>"
        +

        "<span style='color:red;font-size:20px'>●</span> "
        +
        "กลุ่มที่ 1<br>"
        +

        "<span style='color:blue;font-size:20px'>●</span> "
        +
        "กลุ่มที่ 2";


    return div;

};


legend.addTo(map);

</script>


<!-- Bootstrap JS -->

<script
    src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
></script>


<?php include 'footer.php'; ?>


</body>

</html>