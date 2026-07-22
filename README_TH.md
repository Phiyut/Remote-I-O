# ROVENTO Repair WebApp – Production Package

แพ็กเกจนี้เป็น Web Server จริง ไม่ใช่ Static HTML และไม่ใช้ localStorage เป็นฐานข้อมูลหลัก

## ความสามารถ

- Flask + Waitress Web Server
- SQLite เริ่มต้นพร้อมใช้งาน
- Admin ตั้งค่า Microsoft SQL Server จากหน้าเว็บ
- Test Connection ก่อนบันทึก
- สร้างตารางอัตโนมัติเมื่อสลับฐานข้อมูล
- Repair Ticket CRUD ผ่าน REST API
- Login และสิทธิ์ Admin
- เก็บ Config, Log และ SQLite ที่ `C:\ProgramData\ROVENTO\Repair WebApp`
- Build EXE แบบ PyInstaller onedir
- Build Installer ด้วย Inno Setup
- Firewall และ Auto Start ตอน Login Windows

## เริ่มทดสอบ Source

1. ติดตั้ง Python 3.11 x64
2. ดับเบิลคลิก `01_RUN_SOURCE.cmd`
3. เปิด `http://127.0.0.1:5058`

บัญชีเริ่มต้น:

- Username: `admin`
- Password: `admin123`

เปลี่ยน Password ทันทีที่เมนู `Admin · Database`

## Build EXE และ Installer

ดับเบิลคลิก `00_BUILD_MENU.cmd` แล้วเลือกข้อ 4 หรือเปิด `04_BUILD_ALL.cmd`

ผลลัพธ์:

- EXE: `dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-Server.exe`
- Installer: `installer_output\ROVENTO_Repair_WebApp_Setup.exe`

## Microsoft SQL Server

เครื่อง Server ต้องติดตั้ง Microsoft ODBC Driver 17 หรือ 18 for SQL Server ให้ตรงกับค่าที่เลือกในหน้า Admin

ตัวอย่าง:

- Server: `192.168.1.10`
- Port: `1433`
- Database: `ROVENTO_Repair`
- Driver: `ODBC Driver 17 for SQL Server`

User ของ SQL Server ต้องมีสิทธิ์ Connect, SELECT, INSERT, UPDATE, DELETE และ CREATE TABLE สำหรับการตั้งค่าครั้งแรก

## การเข้าจาก LAN

เปิดจากเครื่องอื่นด้วย:

`http://IP-ของเครื่องที่ติดตั้ง:5058`

Installer มีตัวเลือกสร้าง Windows Firewall Rule ให้

## การติดตั้งทับ

Installer จะหยุด Process เดิมก่อนเขียนไฟล์ใหม่ และจะไม่ลบข้อมูลใน `C:\ProgramData\ROVENTO\Repair WebApp`

## หมายเหตุ

การเปลี่ยน Database ไม่ได้ย้ายข้อมูลจาก SQLite ไป MSSQL อัตโนมัติ หากต้องการ Migration ต้องเพิ่มเครื่องมือ Export/Import แยกต่างหาก
