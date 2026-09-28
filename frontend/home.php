<?php
session_start();
?>
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Mackerel Engine | ระบบคาดการณ์การกระจายตัวของปลาทู</title>

<link rel="icon" type="image/png" href="../img/logo.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="../css/menu.css">
<link rel="stylesheet" href="../css/home.css">

</head>

<body>
<?php include 'menu.php'; ?>

<main class="project-home">

<section class="hero-modern">
    <div class="container">
        <div class="row align-items-center g-4">
            <div class="col-lg-8">
                <div class="eyebrow">MACKEREL ENGINE · MACHINE LEARNING PROJECT</div>

                <h1 class="hero-title">
                    ระบบคาดการณ์
                    <span>การกระจายตัวของปลาทู</span>
                    ในทะเลอ่าวไทยโดยใช้
                    <span>ปัญญาประดิษฐ์</span>
                </h1>

                <p class="hero-desc">
                    ระบบประมวลผลข้อมูลมหาสมุทรเชิงวิเคราะห์สำหรับศึกษาความสัมพันธ์ระหว่าง
                    ข้อมูลการจับปลาทู ปัจจัยทางทะเล และสภาพอากาศ พร้อมประยุกต์ใช้
                    Machine Learning เพื่อช่วยแสดงแนวโน้มและระดับการกระจายตัวของปลาทู
                    ในพื้นที่ศึกษา 5 จังหวัด
                </p>

                <div class="hero-actions">
                    <a href="prediction.php" class="btn btn-ocean">เริ่มการคาดการณ์</a>
                    <a href="documentation.php" class="btn btn-soft">ดูวิธีใช้งาน</a>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="quick-panel">
                    <h5>ปัจจัยข้อมูลที่ใช้วิเคราะห์</h5>
                    <p class="text-secondary small mb-0">
                        ข้อมูลสิ่งแวดล้อมและสภาพอากาศที่เชื่อมตามจังหวัด เดือน และปี
                    </p>

                    <div class="factor-grid">
                        <div class="factor"><strong>SST</strong><small>อุณหภูมิผิวน้ำทะเล</small></div>
                        <div class="factor"><strong>Chlorophyll-a</strong><small>คลอโรฟิลล์-เอ</small></div>
                        <div class="factor"><strong>SSS</strong><small>ความเค็มผิวน้ำทะเล</small></div>
                        <div class="factor"><strong>Rainfall</strong><small>ปริมาณน้ำฝน</small></div>
                        <div class="factor"><strong>Wind</strong><small>ความเร็วและทิศทางลม</small></div>
                        <div class="factor"><strong>Pressure</strong><small>ความดันน้ำ</small></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="section-space pt-0">
    <div class="container">
        <div class="row g-3">
            <div class="col-6 col-lg-3">
                <div class="stat-card">
                    <div class="stat-label">Dataset Period</div>
                    <div class="stat-value">2562–2567</div>
                    <div class="stat-note">6 Years</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="stat-card">
                    <div class="stat-label">Study Areas</div>
                    <div class="stat-value">5</div>
                    <div class="stat-note">Provinces</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="stat-card">
                    <div class="stat-label">Machine Learning</div>
                    <div class="stat-value">3</div>
                    <div class="stat-note">Model Types</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="stat-card">
                    <div class="stat-label">Classification</div>
                    <div class="stat-value">3 Levels</div>
                    <div class="stat-note">LOW · MEDIUM · HIGH</div>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="section-space">
    <div class="container">
        <div class="section-heading">
            <h2>Machine Learning ในระบบ</h2>
            <p>แต่ละโมเดลทำหน้าที่ต่างกันเพื่อช่วยให้การวิเคราะห์ข้อมูลปลาทูครอบคลุมมากขึ้น</p>
        </div>

        <div class="row g-4">
            <div class="col-md-4">
                <div class="model-card">
                    <div class="model-no">01</div>
                    <h5>Linear Regression</h5>
                    <p>ประมาณค่าปริมาณปลาทูเชิงตัวเลขจากข้อมูลปัจจัยที่เกี่ยวข้อง และใช้สำหรับดูแนวโน้มของข้อมูล</p>
                </div>
            </div>

            <div class="col-md-4">
                <div class="model-card">
                    <div class="model-no">02</div>
                    <h5>Random Forest Classification</h5>
                    <p>จำแนกระดับปริมาณปลาทูเป็น LOW, MEDIUM และ HIGH เพื่อให้ผลลัพธ์อ่านและเปรียบเทียบได้ง่าย</p>
                </div>
            </div>

            <div class="col-md-4">
                <div class="model-card">
                    <div class="model-no">03</div>
                    <h5>K-Means Clustering</h5>
                    <p>จัดกลุ่มข้อมูลและพื้นที่ที่มีลักษณะใกล้เคียงกัน เพื่อนำไปแสดงผลเชิงพื้นที่บนแผนที่</p>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="section-space pt-0">
    <div class="container">
        <div class="study-banner">
            <div class="row align-items-center g-3">
                <div class="col-lg-8">
                    <h4 class="mb-0 fw-bold">พื้นที่ศึกษาในอ่าวไทยตอนบน</h4>
                    <p>เพชรบุรี · สมุทรสงคราม · สมุทรสาคร · ชลบุรี · สมุทรปราการ</p>
                </div>
                <div class="col-lg-4 text-lg-end">
                    <a href="about.php" class="btn btn-light px-4">เกี่ยวกับโครงงาน</a>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="section-space pt-0">
    <div class="container">
        <div class="section-heading text-center">
            <h2>Project Team</h2>
            <p>สมาชิกผู้พัฒนาระบบ</p>
        </div>

        <div class="row g-4 justify-content-center">
            <div class="col-md-4">
                <div class="member-card">
                    <img src="../img/m1.jpg" class="member-img" alt="นายปัญญากร เขียวชู">
                    <h5>นายปัญญากร เขียวชู</h5>
                    <p>Project Member</p>
                </div>
            </div>

            <div class="col-md-4">
                <div class="member-card">
                    <img src="../img/m2.jpg" class="member-img" alt="นายธีรภัทร พอกแก้ว">
                    <h5>นายธีรภัทร พอกแก้ว</h5>
                    <p>Project Member</p>
                </div>
            </div>

            <div class="col-md-4">
                <div class="member-card">
                    <img src="../img/m3.png" class="member-img" alt="นายสัตยา พอกแก้ว">
                    <h5>นายสัตยา พอกแก้ว</h5>
                    <p>Project Member</p>
                </div>
            </div>
        </div>
    </div>
</section>

</main>

<?php include 'footer.php'; ?>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
