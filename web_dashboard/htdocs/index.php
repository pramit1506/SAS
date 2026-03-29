<?php
// Force no caching - CRITICAL!
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Cache-Control: post-check=0, pre-check=0", false);
header("Pragma: no-cache");
header("Expires: 0");

date_default_timezone_set('Asia/Kolkata');

$db_host = "localhost";
$db_user = "root";
$db_pass = "";
$db_name = "attendance_system";

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    die("<html><head><title>Error</title><link rel=\"stylesheet\" href=\"style.css\"></head><body><div class=\"container\"><h1>Database Connection Failed</h1><p>Error: " . $conn->connect_error . "</p></div></body></html>");
}

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

$today = date('Y-m-d');

$total_students = 0;
$present_today = 0;
$attendance_data = [];

try {
    $result = $conn->query("SELECT COUNT(*) FROM students");
    if ($result) $total_students = $result->fetch_row()[0];

    $stmt = $conn->prepare("SELECT COUNT(DISTINCT roll_number) FROM attendance WHERE DATE(date_time) = ?");
    $stmt->bind_param("s", $today);
    $stmt->execute();
    $result = $stmt->get_result();
    if ($result) $present_today = $result->fetch_row()[0];
    $stmt->close();

    $sql = "SELECT s.roll_number, s.name, a.date_time
            FROM students s
            LEFT JOIN attendance a ON s.roll_number = a.roll_number AND DATE(a.date_time) = ?
            ORDER BY s.roll_number";

    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $today);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            $attendance_data[] = $row;
        }
    }
    $stmt->close();

} catch (mysqli_sql_exception $e) {
    echo "Error fetching data: " . $e->getMessage();
}

$absent_today = $total_students - $present_today;

$conn->close();
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Smart Attendance System - Dashboard</title>
    <link rel="stylesheet" href="style.css?v=<?php echo time(); ?>">
</head>
<body>
    <div class="container">
        <header>
            <h1>Smart Attendance System</h1>
            <div class="date"><?php echo date('F j, Y H:i:s'); ?></div>
        </header>

        <div class="dashboard">
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Students</h3>
                    <p><?php echo $total_students; ?></p>
                </div>
                <div class="stat-box">
                    <h3>Present Today</h3>
                    <p><?php echo $present_today; ?></p>
                </div>
                <div class="stat-box">
                    <h3>Absent Today</h3>
                    <p><?php echo max(0, $absent_today); ?></p>
                </div>
            </div>

            <div class="attendance-list">
                <h2>Today's Attendance (<?php echo date('d-M-Y', strtotime($today)); ?>)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Roll Number</th>
                            <th>Name</th>
                            <th>Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php
                        if (!empty($attendance_data)) {
                            foreach($attendance_data as $row) {
                                $status = $row['date_time'] ? "Present" : "Absent";
                                $time = $row['date_time'] ? date('h:i:s A', strtotime($row['date_time'])) : " - ";
                                echo "<tr>";
                                echo "<td>" . htmlspecialchars($row['roll_number']) . "</td>";
                                echo "<td>" . htmlspecialchars($row['name']) . "</td>";
                                echo "<td>" . $time . "</td>";
                                echo "<td class='" . strtolower($status) . "'>" . $status . "</td>";
                                echo "</tr>";
                            }
                        } else {
                            echo "<tr><td colspan='4'>No students found or no attendance data for today.</td></tr>";
                        }
                        ?>
                    </tbody>
                </table>
            </div>
        </div>
        <footer>
            <p>Smart Attendance System - <?php echo date('Y'); ?> | Last Updated: <?php echo date('Y-m-d H:i:s'); ?></p>
        </footer>
    </div>
</body>
</html>
