<?php

class connect
{
    function conn()
    {
        // Railway Environment Variables
        $host = getenv('MYSQLHOST') ?: '127.0.0.1';
        $dbname = getenv('MYSQLDATABASE') ?: 'projecta';
        $user = getenv('MYSQLUSER') ?: 'root';
        $pass = getenv('MYSQLPASSWORD') ?: '';
        $port = getenv('MYSQLPORT') ?: '3306';

        try {
            $conn = new PDO(
                "mysql:host=$host;port=$port;dbname=$dbname;charset=utf8mb4",
                $user,
                $pass,
                array(
                    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    PDO::ATTR_EMULATE_PREPARES => false
                )
            );

            return $conn;

        } catch (PDOException $e) {
            error_log("Database connection failed: " . $e->getMessage());
            die("ไม่สามารถเชื่อมต่อ Database ได้");
        }
    }

    function query($sql, $params = array())
    {
        $conn = $this->conn();

        $res = $conn->prepare($sql);
        $res->execute($params);

        return $res;
    }

    function counts($res)
    {
        return $res->rowCount();
    }

    function save_logs($action, $uid)
    {
        $sql = "INSERT INTO `logs`
                (`action`, `uid`, `dating`)
                VALUES (?, ?, ?)";

        $this->query(
            $sql,
            array($action, $uid, time())
        );
    }

    function salter($txt)
    {
        $key = 'kerel';

        return hash(
            'sha256', $key . $txt . $key
        );
    }

    function query_lastid($sql, $params = array())
    {
        $conn = $this->conn();

        $res = $conn->prepare($sql);
        $res->execute($params);

        return $conn->lastInsertId();
    }

    function check_acl()
    {
        $option = (
            isset($_REQUEST['option']) &&
            $_REQUEST['option'] != ''
        )
            ? $_REQUEST['option']
            : 'logs';

        if (!isset($_SESSION['uid'])) {
            return 0;
        }

        $uid = $_SESSION['uid'];

        $sql = "SELECT MAX(`acl`.`accl`) AS `mca`
                FROM `app`
                INNER JOIN `acl`
                    ON `acl`.`appid` = `app`.`id`
                INNER JOIN `uig`
                    ON `uig`.`ugid` = `acl`.`ugid`
                WHERE `app`.`dir` = ?
                AND `acl`.`status` = '1'
                AND `uig`.`status` = '1'
                AND `uig`.`uid` = ?";

        $res = $this->query(
            $sql,
            array($option, $uid)
        );

        $cdr = $res->fetch();

        if ($cdr && $cdr['mca'] !== null) {
            return (int)$cdr['mca'];
        }

        return 0;
    }
}
?>