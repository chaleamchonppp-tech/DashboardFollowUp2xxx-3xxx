# เผยแพร่ Dashboard

แอปต้องใช้ Python 3.12, HTTPS, รหัสผ่านเข้าใช้งาน และ disk ถาวรสำหรับประวัติ SAP โดย GitHub Pages ใช้รัน Python/SQLite ไม่ได้

## Render

มี `render.yaml` สำหรับสร้างบริการแบบ Blueprint พร้อม persistent disk 1 GB และ plan Starter (มีค่าใช้จ่าย) เปิด https://render.com/deploy?repo=https://github.com/chaleamchonppp-tech/DashboardFollowUp2xxx-3xxx แล้วเชื่อม GitHub ให้ Render อ่าน repository ได้ ตรวจราคาและตั้ง APP_USERNAME / APP_PASSWORD ในหน้าของ Render จากนั้นสร้างบริการ Blueprint นี้

หากสร้างผ่าน Blueprint ไม่ต้องเพิ่ม disk หรือ environment variables เดิมซ้ำ ค่า secret ที่ `sync: false` ต้องกรอกผ่าน Render เอง ระบบจะไม่เปิดเซิร์ฟเวอร์ถ้ารหัสผ่านสั้นกว่า 12 ตัวอักษร

1. เชื่อมบัญชี Render กับ repository นี้ แล้วสร้าง Web Service แบบ Docker ใช้ Dockerfile ที่ให้ไว้
2. เลือก plan ที่รองรับ persistent disk (มีค่าใช้จ่ายตามบริการ) เพิ่ม disk mount path `/var/data` เพื่อรักษาประวัติหลัง deploy/restart
3. ตั้ง environment variables ในหน้าบริการ:
   - `APP_USERNAME`: ชื่อผู้ใช้ที่ต้องการ
   - `APP_PASSWORD`: รหัสผ่านอย่างน้อย 12 ตัวอักษร กรอกผ่านช่อง secret ของบริการ ห้ามใส่ใน Git หรือแชต
   - `REQUIRE_AUTH=1` และ `DASHBOARD_DB_PATH=/var/data/dashboard.sqlite` มีค่าเริ่มต้นอยู่ใน Dockerfile
4. ตั้ง Health Check Path เป็น `/healthz` แล้ว Deploy
5. เปิด URL HTTPS ของบริการ ล็อกอิน และตรวจงานตามตัวอย่าง 334 งาน จากนั้นลองนำเข้า SAP สัปดาห์ถัดไป

แนะนำหนึ่ง instance เพราะ SQLite ใช้ disk ในเครื่องเดียว ไม่ใช้ free ephemeral storage สำหรับประวัติที่ต้องเก็บถาวร

## VPS / เซิร์ฟเวอร์

Build Dockerfile, mount volume ลง `/var/data`, ตั้ง APP_USERNAME/APP_PASSWORD ผ่านไฟล์ environment ที่ไม่เข้า Git หรือ secret manager แล้วเปิดพอร์ตภายในให้ reverse proxy ที่มี HTTPS โดยให้ proxy ส่ง Authorization header ถึงแอป

## สำรองข้อมูล

สำรอง `/var/data/dashboard.sqlite` ด้วย SQLite backup API หรือหยุดบริการก่อนคัดลอกฐานข้อมูล และเก็บสำรองนอก disk ของบริการ ข้อมูลตั้งต้นใน Git คือข้อมูลวันที่ 5 ต.ค. 2569 ประวัติอัปโหลดหลังจากนั้นอยู่ในฐานข้อมูลเท่านั้น

ก่อนถือว่า deploy สำเร็จต้องตรวจ: ไม่มีรหัสผ่านเรียก `/api/data` ได้ 401, มีรหัสผ่านดูข้อมูลได้, นำเข้าไฟล์ได้ และ restart บริการแล้วประวัติยังอยู่
