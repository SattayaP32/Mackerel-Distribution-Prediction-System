<?php session_start(); ?>
<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="../img/logo.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="../css/menu.css">
<link rel="stylesheet" href="../css/home.css"><title>Documentation | Mackerel Engine</title></head>
<body><?php include 'menu.php'; ?>
<main class="project-home"><section class="inner-page"><div class="container">
<div class="inner-hero"><div class="eyebrow">DOCUMENTATION · USER GUIDE</div>
<h1 class="inner-title">คู่มือการใช้งานระบบ</h1>
<p class="inner-desc">ขั้นตอนพื้นฐานสำหรับเลือกข้อมูล ประมวลผล และทำความเข้าใจผลลัพธ์จาก Machine Learning ภายใน Mackerel Engine</p></div>

<div class="section-space">
<div class="section-heading"><h2>ขั้นตอนการคาดการณ์</h2><p>เลือกข้อมูลตามลำดับก่อนเริ่มประมวลผล</p></div>
<div class="info-grid">
<div class="model-card step-card"><div class="step-no">01</div><div><h5>เลือกเดือนและปี</h5><p>กำหนดช่วงเวลาของข้อมูลที่ต้องการตรวจสอบ</p></div></div>
<div class="model-card step-card"><div class="step-no">02</div><div><h5>เลือกจังหวัด</h5><p>กำหนดพื้นที่ศึกษาที่ต้องการนำมาวิเคราะห์</p></div></div>
<div class="model-card step-card"><div class="step-no">03</div><div><h5>กด Predict</h5><p>ให้ระบบประมวลผลและแสดงผลลัพธ์ของข้อมูลที่เลือก</p></div></div>
</div>
</div>

<div class="section-space pt-0">
<div class="section-heading"><h2>Machine Learning Models</h2><p>ระบบประกอบด้วยโมเดลหลัก 3 รูปแบบ</p></div>
<div class="row g-3">
<div class="col-lg-4"><div class="model-card"><div class="model-no">01</div><h5>Linear Regression</h5><p>ใช้ประมาณปริมาณปลาทูในเชิงตัวเลขและช่วยแสดงแนวโน้มของผลการคาดการณ์</p></div></div>
<div class="col-lg-4"><div class="model-card"><div class="model-no">02</div><h5>Random Forest Classification</h5><p>จำแนกระดับปริมาณปลาทูเป็น LOW, MEDIUM และ HIGH</p></div></div>
<div class="col-lg-4"><div class="model-card"><div class="model-no">03</div><h5>K-Means Clustering</h5><p>จัดกลุ่มข้อมูลที่มีลักษณะใกล้เคียงกันและนำไปใช้กับการแสดงผลเชิงพื้นที่</p></div></div>
</div>
</div>

<div class="study-banner d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
<div><h4 class="mb-1 fw-bold">พร้อมเริ่มวิเคราะห์ข้อมูล</h4><p>เลือกจังหวัด เดือน และปี จากหน้า Prediction</p></div>
<a href="prediction.php" class="btn btn-light fw-bold px-4 py-2">Start Prediction</a>
</div>
</div></section></main>
<?php include 'footer.php'; ?><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body></html>