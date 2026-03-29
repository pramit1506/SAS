<?php
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Pragma: no-cache");
header("Expires: 0");

date_default_timezone_set('Asia/Kolkata');

echo "<h1>🔍 DEBUG INFORMATION</h1>";
echo "<pre>";

// 1. Test database connection
echo "=== DATABASE CONNECTION ===\n";
$conn = new mysqli('localhost', 'root', '', 'attendance_system');

if ($conn->connect_error) {
    echo "❌ CONNECTION FAILED: " . $conn->connect_error . "\n";
    exit;
} else {
    echo "✅ CONNECTION SUCCESS\n";
}

// 2. Check today's date
echo "\n=== DATE CHECK ===\n";
$today = date('Y-m-d');
echo "Today's Date: $today\n";
echo "Current DateTime: " . date('Y-m-d H:i:s') . "\n";

// 3. Count total students
echo "\n=== STUDENTS COUNT ===\n";
$result = $conn->query("SELECT COUNT(*) FROM students");
$row = $result->fetch_row();
echo "Total Students: " . $row[0] . "\n";

// 4. Show ALL attendance records (no date filter)
echo "\n=== ALL ATTENDANCE RECORDS (Last 20) ===\n";
$result = $conn->query("SELECT id, roll_number, date_time FROM attendance ORDER BY id DESC LIMIT 20");
while($row = $result->fetch_assoc()) {
    $date_part = date('Y-m-d', strtotime($row['date_time']));
    $match = ($date_part == $today) ? "✅ TODAY" : "❌ PAST";
    echo "ID: " . $row['id'] . " | Roll: " . $row['roll_number'] . " | DateTime: " . $row['date_time'] . " | " . $match . "\n";
}

// 5. Count TODAY's attendance with date filter
echo "\n=== COUNT TODAY'S ATTENDANCE (Using DATE filter) ===\n";
$query = "SELECT COUNT(*) FROM attendance WHERE DATE(date_time) = '$today'";
echo "Query: $query\n";
$result = $conn->query($query);
$row = $result->fetch_row();
echo "Count: " . $row[0] . "\n";

// 6. Show TODAY's attendance details
echo "\n=== TODAY'S ATTENDANCE DETAILS ===\n";
$query = "SELECT a.id, a.roll_number, s.name, a.date_time 
          FROM attendance a
          LEFT JOIN students s ON a.roll_number = s.roll_number
          WHERE DATE(a.date_time) = '$today'
          ORDER BY a.date_time DESC";
echo "Query: $query\n";
$result = $conn->query($query);
echo "Rows Found: " . $result->num_rows . "\n";
while($row = $result->fetch_assoc()) {
    echo "ID: " . $row['id'] . " | Roll: " . $row['roll_number'] . " | Name: " . $row['name'] . " | Time: " . $row['date_time'] . "\n";
}

$conn->close();

echo "</pre>";
?>
