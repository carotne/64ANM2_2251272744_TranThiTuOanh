# Cấu hình
$table = "oanhlab-prod-conduit" # Tên bảng DynamoDB của bạn
$region = "ap-southeast-1"
$loopCount = 100

Write-Host "Bắt đầu gửi $loopCount request trái phép đến DynamoDB..." -ForegroundColor Yellow

for ($i = 1; $i -le $loopCount; $i++) {
    Write-Host "Request lần thứ $i..."
    # Lệnh cố tình gây lỗi AccessDenied
    aws dynamodb scan --table-name $table --region $region | Out-Null
    
    # Nghỉ 0.5 giây giữa mỗi request để không bị API Gateway chặn quá nhanh
    Start-Sleep -Milliseconds 500
}

Write-Host "Đã gửi xong. Hãy kiểm tra CloudTrail hoặc GuardDuty trong vài phút tới." -ForegroundColor Green