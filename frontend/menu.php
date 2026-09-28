<nav class="navbar navbar-light bg-light shadow-sm">

    <div class="container-fluid">

        <a class="navbar-brand d-flex align-items-center"
           href="home.php">

            <img src="../img/logo.png"
                 alt="Logo"
                 class="navbar-logo me-2">

            <strong>
                Mackerel Engine
            </strong>

        </a>

        <div class="navbar-center">

            <ul class="nav">

                <li class="nav-item">
                    <a class="nav-link"
                       href="home.php">
                        Home
                    </a>
                </li>

                <li class="nav-item">
                    <a class="nav-link"
                       href="about.php">
                        About
                    </a>
                </li>

                <li class="nav-item">
                    <a class="nav-link"
                       href="documentation.php">
                        Documentation
                    </a>
                </li>

                <li class="nav-item">
                    <a class="nav-link"
                       href="contact.php">
                        Contact
                    </a>
                </li>

                <li class="nav-item">
                    <a class="nav-link"
                       href="profile.php">
                        Profile
                    </a>
                </li>

            </ul>

        </div>

        <button class="btn btn-primary"
                type="button"
                data-bs-toggle="offcanvas"
                data-bs-target="#sidebar">

            ☰ Menu

        </button>

    </div>

</nav>

<div class="offcanvas offcanvas-start"
     tabindex="-1"
     id="sidebar">

    <div class="offcanvas-header">

        <h5 class="offcanvas-title">

            Menu

        </h5>

        <button type="button"
                class="btn-close"
                data-bs-dismiss="offcanvas">
        </button>

    </div>

    <div class="offcanvas-body">

        <div class="text-center mb-4">

            <img src="../img/logo.png"
                 class="logo"
                 alt="Logo">

            <h5 class="sidebar-title mt-3">
                Mackerel Engine
            </h5>

            <small class="sidebar-subtitle text-muted">
                AI Forecast System
            </small>

        </div>

        <div class="list-group">

            <!-- Dashboard -->

            <div class="list-group-item active section-title">
                Dashboard
            </div>

            <a href="home.php"
               class="list-group-item list-group-item-action">
                Home
            </a>

            <!-- Dataset -->

            <div class="list-group-item active mt-3 section-title">
                Archive
            </div>

            <a href="station.php"
               class="list-group-item list-group-item-action">
                Station
            </a>

            <a href="dataset.php"
               class="list-group-item list-group-item-action">
                Dataset
            </a>

            <a href="environment.php"
               class="list-group-item list-group-item-action">
                Environment
            </a>

            <a href="weather.php"
               class="list-group-item list-group-item-action">
                Weather
            </a>

            <!-- AI Models -->

            <div class="list-group-item active mt-3 section-title">
                AI Models
            </div>

            <a href="regression.php"
               class="list-group-item list-group-item-action">
                Regression
            </a>

            <a href="classification.php"
               class="list-group-item list-group-item-action">
                Classification
            </a>

            <a href="clustering.php"
               class="list-group-item list-group-item-action">
                Clustering
            </a>

            <a href="prediction.php"
               class="list-group-item list-group-item-action">
                Prediction
            </a>

            <!-- System -->

            <div class="list-group-item active mt-3 section-title">
                System
            </div>

            <a href="../backend/index.php?option=users&task=def"
               class="list-group-item list-group-item-action">
                Backend
            </a>

        </div>

    </div>

</div>