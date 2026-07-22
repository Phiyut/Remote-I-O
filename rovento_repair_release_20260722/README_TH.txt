ROVENTO Repair WebApp 1.0.0
========================================

คุณสมบัติ
- Web Server รันด้วย Flask + Waitress ที่ 0.0.0.0:5058
- ข้อมูล Ticket เก็บในฐานข้อมูลส่วนกลาง ไม่ใช้ Browser localStorage
- SQLite พร้อมใช้งานทันที
- Admin ตั้งค่า Microsoft SQL Server หรือ PostgreSQL จากหน้าเว็บได้
- ค่า Config และ Database เก็บที่ C:\ProgramData\ROVENTO\Repair WebApp
- PyInstaller แบบ onedir
- Inno Setup รองรับติดตั้งทับ, Startup และ Firewall

บัญชีเริ่มต้น
- Admin: rovento / rovento
- Technician: T001 / 1234
- Supervisor: S001 / 1234

ทดสอบ Source
1. ติดตั้ง Python 3.11 x64
2. ดับเบิลคลิก 01_RUN_SOURCE.cmd
3. เปิด http://127.0.0.1:5058

สร้าง EXE และ Installer
1. ดับเบิลคลิก 00_BUILD_MENU_CLICK_ME.cmd
2. เลือก 4. Build EXE + Installer
3. EXE อยู่ใน dist\ROVENTO-Repair-WebApp
4. Installer อยู่ใน installer_output\ROVENTO_Repair_WebApp_Setup.exe

ตั้งค่าฐานข้อมูล
1. Login ด้วย Admin
2. เปิดเมนู Admin · Database
3. เลือก SQLite / Microsoft SQL Server / PostgreSQL
4. กด Test Connection
5. กด Save Configuration
6. ปิดและเปิด ROVENTO Repair WebApp ใหม่

SQL Server
- เครื่อง Server ต้องติดตั้ง ODBC Driver 17 หรือ 18 for SQL Server
- เปิด TCP/IP ของ SQL Server และกำหนด Port เช่น 1433
- Database ต้องถูกสร้างไว้ก่อนในเวอร์ชันนี้

LAN
- Server URL: http://<SERVER-IP>:5058
- Installer สามารถสร้าง Windows Firewall Rule ให้โดยอัตโนมัติ

หมายเหตุ
- การติดตั้งทับจะไม่ลบข้อมูลใน C:\ProgramData\ROVENTO\Repair WebApp
- ควรเปลี่ยนรหัสผ่าน Admin หลังติดตั้งครั้งแรก
