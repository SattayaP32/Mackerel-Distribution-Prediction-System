<?php session_start(); ?>
<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="../img/logo.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="../css/menu.css">
<link rel="stylesheet" href="../css/home.css"><title>About Project | Mackerel Engine</title></head>
<body><?php include 'menu.php'; ?>
<main class="project-home">
<section class="inner-page"><div class="container">
<div class="inner-hero">
<div class="eyebrow">ABOUT PROJECT · MACKEREL ENGINE</div>
<h1 class="inner-title">เกี่ยวกับโครงงาน</h1>
<p class="inner-desc">ระบบคาดการณ์การกระจายตัวของปลาทูในทะเลอ่าวไทยโดยใช้ปัญญาประดิษฐ์ โดยนำข้อมูลปลาทู ข้อมูลทางทะเล และข้อมูลสภาพอากาศมาวิเคราะห์ร่วมกัน</p>
</div>

<div class="section-space">
<div class="section-heading"><h2>วัตถุประสงค์ของโครงงาน</h2><p>แนวทางหลักในการพัฒนาและประยุกต์ใช้ระบบ</p></div>
<div class="info-grid">
<div class="model-card"><div class="model-no">01</div><h5>Machine Learning</h5><p>พัฒนาโมเดลสำหรับประมาณปริมาณ จำแนกระดับ และจัดกลุ่มข้อมูลที่เกี่ยวข้องกับปลาทู</p></div>
<div class="model-card"><div class="model-no">02</div><h5>Ocean Data Analysis</h5><p>วิเคราะห์ข้อมูลสภาพแวดล้อมทางทะเลและสภาพอากาศร่วมกับข้อมูลปริมาณปลาทู</p></div>
<div class="model-card"><div class="model-no">03</div><h5>Web Application</h5><p>นำผลการวิเคราะห์มาแสดงผ่านตาราง กราฟ แผนที่ และหน้าคาดการณ์ที่เข้าใจได้ง่าย</p></div>
</div>
</div>

<div class="section-space pt-0">
<div class="section-heading"><h2>ข้อมูลที่จัดเก็บในระบบ</h2><p>ปัจจัยหลักที่จัดเก็บและนำมาใช้ในการทดลอง</p></div>
<div class="quick-panel">
<div class="info-chip-list">
<span class="info-chip">SST</span><span class="info-chip">Chlorophyll-a</span><span class="info-chip">Sea Surface Salinity</span>
<span class="info-chip">Rainfall</span><span class="info-chip">Wind Speed</span><span class="info-chip">Sea Level Pressure</span>
<span class="info-chip">Air Temperature</span><span class="info-chip">Wind Direction</span>
<span class="info-chip">Monsoon</span><span class="info-chip">Fishery Catch</span>
</div>
</div>
</div>

<div class="study-banner">
<h4 class="mb-1 fw-bold">พื้นที่ศึกษา 5 จังหวัด · ข้อมูลปี 2562–2567</h4>
<p>เพชรบุรี · สมุทรสงคราม · สมุทรสาคร · ชลบุรี · สมุทรปราการ</p>
</div>
</div></section>
</main>
<?php include 'footer.php'; ?><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body></html>