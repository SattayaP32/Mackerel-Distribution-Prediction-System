<?php

class users
{

    function def()
    {
        $conn = new connect();
        $acl = $conn->check_acl();

        ?>

        <div class='container'>

            <div class='row'>

                <div class='col-12'>

                <h2>User Management</h2>

                <?php

                // Admin สามารถ Add User ได้
                if (($acl == '2') or ($acl > '5'))
                {
                ?>

                    <input type='button'
                           value='Add'
                           onclick='window.open("index.php?option=users&task=edit&id=0","_self")'>

                <?php
                }
                ?>

                <input type='hidden' name='option' value='users'>
                <input type='hidden' name='task' value='def'>

                </form>

                <table id='datatable' class='table table-bordered table-striped'>

                    <thead>

                        <tr>


                            <th class='text-center'>user</th>

                            <th class='text-center'>Name</th>

                            <th class='text-center'>Surname</th>

                            <th class='text-center'>Email</th>

                            <th class='text-center'>Status</th>

                            <th class='text-center'>Action</th>

                        </tr>

                    </thead>

                    <tbody>

                        <?php


                        if (($acl == '2') or ($acl > '5'))
                        {
                            $sql = "select * from `users`";
                        }
                        else
                        {
                            $sql = "select * from `users`
                                    where `id` = '".$_SESSION['uid']."'";
                        }

                        $res = $conn->query($sql);

                        while ($cdr = $res->fetch())
                        {

                            echo "<tr>";


                            echo "<td>";
                            echo $cdr['user'];
                            echo "</td>";

                            echo "<td>";
                            echo $cdr['name'];
                            echo "</td>";

                            echo "<td>";
                            echo $cdr['surname'];
                            echo "</td>";

                            echo "<td>";
                            echo $cdr['mail'];
                            echo "</td>";

                            echo "<td>";

                            if ($cdr['status'] == 1)
                            {
                                echo "Active";

                                $ds = "In-Active";
                                $dss = "0";
                            }
                            else
                            {
                                echo "In-Active";

                                $ds = "Active";
                                $dss = "1";
                            }

                            echo "</td>";

                            echo "<td>";


                            if (($acl == '2') or ($acl > '5'))
                            {

                                echo "<input type='button'
                                      value='Edit'
                                      onclick='window.open(\"index.php?option=users&task=edit&id=".$cdr['id']."\",\"_self\")' />";

                                echo " ";

                                echo "<input type='button'
                                      value='".$ds."'
                                      onclick='if(confirm(\"Are you sure?\")) window.location=\"index.php?option=users&task=del&id=".$cdr['id']."&stat=".$dss."\"' />";

                                echo " ";

                                echo "<input type='button'
                                      value='Detail'
                                      onclick='window.open(\"index.php?option=users&task=det&id=".$cdr['id']."\",\"_self\")' />";

                            }
                            else
                            {

                                /*
                                 * User ทั่วไป
                                 * แก้/ดูได้เฉพาะตัวเอง
                                 * ไม่มี Active / In-Active
                                 */

                                echo "<input type='button'
                                      value='Edit'
                                      onclick='window.open(\"index.php?option=users&task=edit&id=".$cdr['id']."\",\"_self\")' />";

                                echo " ";

                                echo "<input type='button'
                                      value='Detail'
                                      onclick='window.open(\"index.php?option=users&task=det&id=".$cdr['id']."\",\"_self\")' />";

                            }

                            echo "</td>";

                            echo "</tr>";
                        }

                        ?>

                    </tbody>

                </table>

                </div>

            </div>

        </div>

        <?php
    }


    function edit()
    {

        $conn = new connect();

        $acl = $conn->check_acl();

        $id = $_REQUEST['id'];


        /*
         * User ทั่วไป
         * ห้าม Add User ใหม่
         * และห้ามแก้ User คนอื่น
         */

        if (($acl != '2') and ($acl <= '5'))
        {

            if ($id == '0')
            {
                header('location:index.php?option=users&task=def');
                exit();
            }

            if ($id != $_SESSION['uid'])
            {
                header('location:index.php?option=users&task=def');
                exit();
            }

        }


        if ($id == 0)
        {

            $name = "";
            $surname = "";
            $user = "";
            $pass = "";
            $mail = "";

        }
        else
        {

            $sql = "select * from `users`
                    where `id` = '".$id."'";

            $res = $conn->query($sql);

            while ($cdr = $res->fetch())
            {

                $name = $cdr['name'];
                $surname = $cdr['surname'];
                $user = $cdr['user'];
                $pass = $cdr['pass'];
                $mail = $cdr['mail'];

            }

        }

        ?>

        <div class='container'>

            <div class='row'>

                <div class='col-12'>

                <h2>User Management</h2>

                <form action='index.php' method='get'>

                <table class='table'>

                    <thead>

                        <tr>

                            <th colspan='2' class='text-center'>
                                Edit Data
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        <tr>

                            <td>Name</td>

                            <td>

                                <input name='name'
                                       value='<?php echo $name;?>'>

                            </td>

                        </tr>


                        <tr>

                            <td>Surname</td>

                            <td>

                                <input name='surname'
                                       value='<?php echo $surname;?>'>

                            </td>

                        </tr>


                        <tr>

                            <td>user</td>

                            <td>

                                <input name='user'
                                       value='<?php echo $user;?>'>

                            </td>

                        </tr>


                        <tr>

                            <td>Password</td>

                            <td>

                                <input type='password'
                                       name='pass'
                                       value='<?php echo $pass;?>'>

                            </td>

                        </tr>


                        <tr>

                            <td>Email</td>

                            <td>

                                <input type='mail'
                                       name='mail'
                                       value='<?php echo $mail;?>'>

                            </td>

                        </tr>


                        <tr>

                            <td colspan='2' class='text-center'>

                                <input type='hidden'
                                       name='option'
                                       value='users'>

                                <input type='hidden'
                                       name='task'
                                       value='save'>

                                <input type='hidden'
                                       name='id'
                                       value='<?php echo $id;?>'>

                                <input type='submit'
                                       value='Save'>

                                <input type='button'
                                       value='Back'
                                       onclick='window.open("index.php?option=users&task=def","_self")'>

                            </td>

                        </tr>

                    </tbody>

                </table>

                </form>

                </div>

            </div>

        </div>

        <?php
    }


    function del()
    {

        $id = $_REQUEST['id'];

        $conn = new connect();

        $acl = $conn->check_acl();


        /*
         * User ทั่วไป
         * ห้าม Active / In-Active User คนอื่น
         */

        if (($acl != '2') and ($acl <= '5'))
        {

            if ($id != $_SESSION['uid'])
            {
                header('location:index.php?option=users&task=def');
                exit();
            }

            /*
             * ไม่ให้ User ทั่วไปเปลี่ยน Status ตัวเอง
             */

            header('location:index.php?option=users&task=def');
            exit();

        }


        /*
         * Admin สามารถเปลี่ยน Status ได้
         */

        $sql = "update `users`
                set `status` = '".$_REQUEST['stat']."'
                where `id` = '".$id."'";

        $conn->query($sql);

        header('location:index.php?option=users&task=def');

        exit();
    }


    function save()
    {

        $conn = new connect();

        $acl = $conn->check_acl();

        $id = $_REQUEST['id'];


        /*
         * User ทั่วไป
         * แก้ได้เฉพาะข้อมูลของตัวเอง
         * และห้ามสร้าง User ใหม่
         */

        if (($acl != '2') and ($acl <= '5'))
        {

            if ($id == '0')
            {
                header('location:index.php?option=users&task=def');
                exit();
            }

            if ($id != $_SESSION['uid'])
            {
                header('location:index.php?option=users&task=def');
                exit();
            }

        }


        $name = $_REQUEST['name'];

        $surname = $_REQUEST['surname'];

        $user = $_REQUEST['user'];

        $mail = $_REQUEST['mail'];


        // เข้ารหัส Password ด้วย salter

        $pass = $conn->salter($_REQUEST['pass']);


        if ($id == 0)
        {

            /*
             * Admin เพิ่ม User
             */

            $sql = "insert into `users`
                    set `name` = '".$name."',
                    `user` = '".$user."',
                    `surname` = '".$surname."',
                    `pass` = '".$pass."',
                    `mail` = '".$mail."',
                    `status` = '1'";

        }
        else
        {

            /*
             * แก้ไข User
             */

            $sql = "update `users`
                    set `name` = '".$name."',
                    `user` = '".$user."',
                    `surname` = '".$surname."',
                    `pass` = '".$pass."',
                    `mail` = '".$mail."'
                    where `id` = '".$id."'";

        }


        $conn->query($sql);

        header('location:index.php?option=users&task=def');

        exit();
    }


    function det()
    {

        $id = $_REQUEST['id'];

        $conn = new connect();

        $acl = $conn->check_acl();


        /*
         * User ทั่วไป
         * ดูได้เฉพาะข้อมูลตัวเอง
         */

        if (($acl != '2') and ($acl <= '5'))
        {

            if ($id != $_SESSION['uid'])
            {
                header('location:index.php?option=users&task=def');
                exit();
            }

        }


        $sql = "select * from `users`
                where `id` = '".$id."'";

        $res = $conn->query($sql);

        while ($cdr = $res->fetch())
        {

            $name = $cdr['name'];

            $surname = $cdr['surname'];

            $user = $cdr['user'];

            $pass = $cdr['pass'];

            $mail = $cdr['mail'];

        }

        ?>

        <div class='container'>

            <div class='row'>

                <div class='col-12'>

                <h2>User Management</h2>

                <table class='table'>

                    <thead>

                        <tr>

                            <th colspan='2' class='text-center'>
                                user Data
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        <tr>

                            <td>Name</td>

                            <td>

                                <?php echo $name;?>

                            </td>

                        </tr>


                        <tr>

                            <td>surname</td>

                            <td>

                                <?php echo $surname;?>

                            </td>

                        </tr>


                        <tr>

                            <td>user</td>

                            <td>

                                <?php echo $user;?>

                            </td>

                        </tr>


                        <tr>

                            <td>Email</td>

                            <td>

                                <?php echo $mail;?>

                            </td>

                        </tr>


                        <tr>

                            <td colspan='2' class='text-center'>

                                <input type='button'
                                       value='Back'
                                       onclick='window.open("index.php?option=users&task=def","_self")'>

                            </td>

                        </tr>

                    </tbody>

                </table>

                </div>

            </div>

        </div>

        <?php
    }

}

?>