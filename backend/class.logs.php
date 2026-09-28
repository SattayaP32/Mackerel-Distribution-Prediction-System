<?php

class logs
{
	
	function def()
	{
		$conn = new connect();
		$acl = $conn->check_acl();

		if (($acl == '2') or ($acl > '5'))
		{
			// Admin เห็น Logs ของทุกคน
			$sql = "select *
					from `logs`
					left join `users`
					on `users`.`id` = `logs`.`uid`
					order by `logs`.`dating` desc";
		}
		else
		{
			// User ทั่วไปเห็นเฉพาะ Logs ของตัวเอง
			$sql = "select *
					from `logs`
					left join `users`
					on `users`.`id` = `logs`.`uid`
					where `logs`.`uid` = '".$_SESSION['uid']."'
					order by `logs`.`dating` desc";
		}

		$res = $conn->query($sql);
	?>

	<div class='container'>
		<div class='row'>
			<div class='col-12'>

				<h2>Logs</h2>

				<table id='datatable' class='table table-bordered table-striped'>

					<thead>

						<tr>
							<th class='text-center'>No</th>
							<th class='text-center'>Users</th>
							<th class='text-center'>Action</th>
							<th class='text-center'>Date</th>
						</tr>

					</thead>

					<tbody>

					<?php

					$a = 1;

					while ($cdr = $res->fetch())
					{
						echo "<tr>";

						echo "<td>";
						echo $a;
						echo "</td>";

						echo "<td>";
						echo $cdr['user'];
						echo "</td>";

						echo "<td>";
						echo $cdr['action'];
						echo "</td>";

						echo "<td>";
						echo date("d/m/Y H:i:s",$cdr['dating']);
						echo "</td>";

						echo "</tr>";

						$a++;
					}

					?>

					</tbody>

				</table>

			</div>
		</div>
	</div>

	<?php
	}
	
	
	function login_form()
	{
	?>

	<div class='container'>
		<div class='row'>
			<div class='col-12'>

				<form action='index.php' method='post'>

					<table class='table'>

						<tr>
							<td colspan='2' class='text-center'>
								Login
							</td>
						</tr>

						<tr>
							<td>
								Username
							</td>

							<td>
								<input name='user'>
							</td>
						</tr>

						<tr>
							<td>
								Password
							</td>

							<td>
								<input type='password' name='pass'>
							</td>
						</tr>

						<tr>

							<td colspan='2' class='text-center'>

								<input type='submit' value='Login'>

								<input type='hidden'
									   name='option'
									   value='logs'>

								<input type='hidden'
									   name='task'
									   value='login'>

							</td>

						</tr>

						<tr>

							<td colspan='2'
								class='text-center text-danger'>

								<?php

								if ((isset($_REQUEST['cc'])) &&
									($_REQUEST['cc'] == 0))
								{
									echo "Username or Password is wrong";
								}

								?>

							</td>

						</tr>

					</table>

				</form>

			</div>
		</div>
	</div>

	<?php
	}
	
	
	function login()
	{
		$conn = new connect();

		$user = $_REQUEST['user'] ?? '';
		$pass = $_REQUEST['pass'] ?? '';

		/*
		 * ใช้ salter() เหมือนระบบเดิม
		 */
		$secure_pass = $conn->salter($pass);

		$sql = "select *
				from `users`
				where `user` = '".$user."'
				and `pass` = '".$secure_pass."'
				and `status` = '1'";

		$res = $conn->query($sql);

		if ($cdr = $res->fetch())
		{
			$cc = 1;

			/*
			 * เก็บ Session ของ User
			 */
			$_SESSION['uid'] = $cdr['id'];
			$_SESSION['uname'] = $cdr['name'];

			/*
			 * บันทึก Login
			 */
			$this->save_logs("login",$cdr['id']);
		}
		else
		{
			$cc = 0;

			/*
			 * Login ไม่สำเร็จ
			 */
			$this->save_logs("cannot login","0");
		}

		header('location:index.php?cc=' . $cc);
		exit();
	}
	
	
	function logout()
	{
		/*
		 * บันทึก Logout ก่อนทำลาย Session
		 */
		if (isset($_SESSION['uid']))
		{
			$this->save_logs("logout",$_SESSION['uid']);
		}

		session_destroy();

		header('location:index.php');
		exit();
	}
	
	
	function save_logs($action,$uid)
	{
		$conn = new connect();

		$sql = "insert into `logs`
				set `action` = '".$action."',
					`uid` = '".$uid."',
					`dating` = '".time()."'";

		$res = $conn->query($sql);
	}
	
}

?>