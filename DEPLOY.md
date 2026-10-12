# เผยแพร่บน GitHub Pages

เว็บไซต์รุ่นหลักไม่ต้องใช้ Render ไม่ต้องสมัครบริการเสียเงิน ไม่ต้องตั้ง User/Password อ่าน SAP ในเบราว์เซอร์และเก็บประวัติในเครื่องผู้ใช้

## GitHub Pages

Workflow `.github/workflows/pages.yml` ทำงานเมื่อ push สาขา main: ตรวจ parser → สร้าง `_site` → deploy GitHub Pages

หาก Pages ยังไม่เปิด: GitHub repository → Settings → Pages → Source: GitHub Actions แล้วรัน workflow “Deploy dashboard to GitHub Pages” ในแท็บ Actions

เว็บไซต์ของ repository นี้: https://chaleamchonppp-tech.github.io/DashboardFollowUp2xxx-3xxx/ (ใช้เมื่อ workflow deploy สำเร็จ)

GitHub Pages ให้บริการฟรีสำหรับ public repository ภายใต้โควตาของ GitHub หน้าตาเว็บไซต์ใช้เหมือนเดิม ทุกคนที่เข้าลิงก์เห็นข้อมูลตั้งต้นที่รวมในเว็บไซต์ ส่วนไฟล์ที่นำเข้าใหม่ไม่ถูกอัปโหลดไป GitHub

## ประวัติ

ข้อมูลนำเข้าอยู่ใน IndexedDB ของเบราว์เซอร์เครื่องนั้น หากเปลี่ยนเครื่อง เปลี่ยนเบราว์เซอร์ หรือโดเมน เปลี่ยนจาก Render มา Pages หรือล้างข้อมูลเว็บไซต์ ต้องกู้คืนประวัติจาก JSON สำรอง การส่งออก CSV ไม่ใช่ไฟล์สำหรับคืนประวัติ

ระบบกู้คืนรวมประวัติให้โดยไม่เขียนทับวันที่เดิม หากวันที่เดียวกันขัดแย้งจะปฏิเสธทั้งชุด

## ต่างจาก Render อย่างไร

หน้าตาเหมือนกัน GitHub Pages ไม่มี Python/SQLite กลาง จึงเก็บประวัติแยกต่อเครื่อง Render รันเซิร์ฟเวอร์ได้ ทำให้หลายเครื่องใช้ฐานข้อมูลเดียวกัน แต่ plan ฟรีไม่มี disk ถาวร ประวัติบนเซิร์ฟเวอร์อาจหายเมื่อ restart/redeploy

ไฟล์ Render เดิมเก็บไว้เผื่อใช้งานอีกครั้ง: plan free, ไม่มี paid disk, REQUIRE_AUTH=0 ถ้าต้องการโหมดเซิร์ฟเวอร์เปิด URL พร้อม `?storage=server`; ไม่จำเป็นต้องสร้าง Render สำหรับใช้งาน Pages
