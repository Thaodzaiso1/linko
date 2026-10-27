-- ============================================================
-- 02_sample_data.sql
-- Dữ liệu mẫu thực tế cho Hệ thống Mạng xã hội Nội bộ
-- Khoảng 120 nhân viên, 12 phòng ban, 25 dự án
-- ============================================================

-- 1. DEPARTMENTS
INSERT INTO departments (department_name, location) VALUES ('Ban Giám đốc', 'Tầng 10 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Công nghệ', 'Tầng 7 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Sản phẩm', 'Tầng 6 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Marketing', 'Tầng 5 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Nhân sự', 'Tầng 4 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Tài chính', 'Tầng 4 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Kinh doanh', 'Tầng 3 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Phòng Chăm sóc KH', 'Tầng 2 - HQ');
INSERT INTO departments (department_name, location) VALUES ('Chi nhánh Hà Nội', 'Hà Nội');
INSERT INTO departments (department_name, location) VALUES ('Chi nhánh Đà Nẵng', 'Đà Nẵng');
INSERT INTO departments (department_name, location) VALUES ('Chi nhánh Cần Thơ', 'Cần Thơ');
INSERT INTO departments (department_name, location) VALUES ('Trung tâm R&D', 'Tầng 8 - HQ');

-- 2. EMPLOYEES (120 nhân viên)
-- Ban Giám đốc
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Nguyễn Văn An', 'an.nguyen@company.vn', 'Tổng Giám đốc', 1, DATE '2015-03-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trần Thị Bình', 'binh.tran@company.vn', 'Phó Tổng Giám đốc', 1, DATE '2016-07-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lê Minh Cường', 'cuong.le@company.vn', 'Giám đốc Công nghệ', 2, DATE '2017-01-10');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phạm Thu Dung', 'dung.pham@company.vn', 'Giám đốc Sản phẩm', 3, DATE '2017-05-20');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hoàng Văn Em', 'em.hoang@company.vn', 'Giám đốc Marketing', 4, DATE '2018-02-01');

-- Phòng Công nghệ (nhiều người)
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Võ Thị Phương', 'phuong.vo@company.vn', 'Trưởng phòng Backend', 2, DATE '2018-06-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đặng Quốc Huy', 'huy.dang@company.vn', 'Trưởng phòng Frontend', 2, DATE '2018-09-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Bùi Minh Tuấn', 'tuan.bui@company.vn', 'Tech Lead', 2, DATE '2019-01-20');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Ngô Thị Lan', 'lan.ngo@company.vn', 'Senior Backend Dev', 2, DATE '2019-04-10');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đỗ Văn Khoa', 'khoa.do@company.vn', 'Senior Frontend Dev', 2, DATE '2019-07-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lý Thị Mai', 'mai.ly@company.vn', 'Backend Developer', 2, DATE '2020-02-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trương Văn Nam', 'nam.truong@company.vn', 'Frontend Developer', 2, DATE '2020-05-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phan Thị Oanh', 'oanh.phan@company.vn', 'DevOps Engineer', 2, DATE '2020-08-20');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Vũ Minh Phát', 'phat.vu@company.vn', 'QA Engineer', 2, DATE '2021-01-10');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đinh Thị Quỳnh', 'quynh.dinh@company.vn', 'Data Engineer', 2, DATE '2021-03-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Cao Văn Rồng', 'rong.cao@company.vn', 'Backend Developer', 2, DATE '2021-06-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lâm Thị Sương', 'suong.lam@company.vn', 'Frontend Developer', 2, DATE '2021-09-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Tô Văn Tâm', 'tam.to@company.vn', 'Mobile Developer', 2, DATE '2022-01-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hồ Thị Uyên', 'uyen.ho@company.vn', 'UI/UX Designer', 2, DATE '2022-04-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Ngô Văn Vinh', 'vinh.ngo@company.vn', 'Junior Backend', 2, DATE '2023-02-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lê Thị Xuân', 'xuan.le@company.vn', 'Junior Frontend', 2, DATE '2023-05-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trần Văn Yên', 'yen.tran@company.vn', 'Intern Dev', 2, DATE '2024-07-01');

-- Phòng Sản phẩm
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Nguyễn Thị Ánh', 'anh.nguyen@company.vn', 'Product Manager', 3, DATE '2019-03-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phạm Văn Bảo', 'bao.pham@company.vn', 'Product Owner', 3, DATE '2020-01-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hoàng Thị Cẩm', 'cam.hoang@company.vn', 'Business Analyst', 3, DATE '2020-06-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đặng Văn Dũng', 'dung.dang@company.vn', 'Product Designer', 3, DATE '2021-02-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Võ Thị Hà', 'ha.vo@company.vn', 'Junior PM', 3, DATE '2022-08-01');

-- Phòng Marketing
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lê Văn Hùng', 'hung.le@company.vn', 'Marketing Manager', 4, DATE '2018-11-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trần Thị Hương', 'huong.tran@company.vn', 'Content Lead', 4, DATE '2019-08-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Nguyễn Văn Khánh', 'khanh.nguyen@company.vn', 'SEO Specialist', 4, DATE '2020-03-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phạm Thị Linh', 'linh.pham@company.vn', 'Social Media', 4, DATE '2021-01-20');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hoàng Văn Minh', 'minh.hoang@company.vn', 'Performance Marketer', 4, DATE '2021-07-01');

-- Phòng Nhân sự
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đỗ Thị Nga', 'nga.do@company.vn', 'HR Manager', 5, DATE '2017-09-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Bùi Văn Phong', 'phong.bui@company.vn', 'Recruiter', 5, DATE '2019-05-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Ngô Thị Quyên', 'quyen.ngo@company.vn', 'HR Specialist', 5, DATE '2020-10-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lý Văn Sơn', 'son.ly@company.vn', 'Training Officer', 5, DATE '2021-04-15');

-- Phòng Tài chính
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trương Thị Tâm', 'tam.truong@company.vn', 'CFO', 6, DATE '2016-12-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phan Văn Uy', 'uy.phan@company.vn', 'Accountant Lead', 6, DATE '2018-04-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Vũ Thị Vân', 'van.vu@company.vn', 'Accountant', 6, DATE '2020-02-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đinh Văn Xuân', 'xuan.dinh@company.vn', 'Financial Analyst', 6, DATE '2021-08-01');

-- Phòng Kinh doanh
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Cao Thị Yến', 'yen.cao@company.vn', 'Sales Director', 7, DATE '2017-06-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lâm Văn An', 'an.lam@company.vn', 'Account Manager', 7, DATE '2019-02-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Tô Thị Bình', 'binh.to@company.vn', 'Sales Executive', 7, DATE '2020-07-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hồ Văn Cường', 'cuong.ho@company.vn', 'Sales Executive', 7, DATE '2021-03-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Ngô Thị Dung', 'dung.ngo@company.vn', 'Sales Support', 7, DATE '2022-01-10');

-- Phòng CSKH
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lê Văn Em', 'em.le@company.vn', 'CS Manager', 8, DATE '2018-08-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trần Thị Phương', 'phuong.tran@company.vn', 'Support Lead', 8, DATE '2019-11-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Nguyễn Văn Huy', 'huy.nguyen@company.vn', 'Customer Support', 8, DATE '2020-09-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phạm Thị Lan', 'lan.pham@company.vn', 'Customer Support', 8, DATE '2021-05-01');

-- Chi nhánh Hà Nội
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hoàng Văn Khoa', 'khoa.hoang@company.vn', 'Giám đốc Chi nhánh HN', 9, DATE '2018-01-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đặng Thị Mai', 'mai.dang@company.vn', 'Sales Manager HN', 9, DATE '2019-06-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Võ Văn Nam', 'nam.vo@company.vn', 'Tech Lead HN', 9, DATE '2020-03-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Bùi Thị Oanh', 'oanh.bui@company.vn', 'Developer HN', 9, DATE '2021-01-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Ngô Văn Phát', 'phat.ngo@company.vn', 'Sales HN', 9, DATE '2021-07-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lý Thị Quỳnh', 'quynh.ly@company.vn', 'Support HN', 9, DATE '2022-02-01');

-- Chi nhánh Đà Nẵng
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trương Văn Rồng', 'rong.truong@company.vn', 'Giám đốc Chi nhánh DN', 10, DATE '2019-04-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Phan Thị Sương', 'suong.phan@company.vn', 'Sales Manager DN', 10, DATE '2020-05-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Vũ Văn Tâm', 'tam.vu@company.vn', 'Developer DN', 10, DATE '2021-02-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Đinh Thị Uyên', 'uyen.dinh@company.vn', 'Support DN', 10, DATE '2021-09-01');

-- Chi nhánh Cần Thơ
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Cao Văn Vinh', 'vinh.cao@company.vn', 'Giám đốc Chi nhánh CT', 11, DATE '2019-08-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lâm Thị Xuân', 'xuan.lam@company.vn', 'Sales Manager CT', 11, DATE '2020-10-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Tô Văn Yên', 'yen.to@company.vn', 'Sales CT', 11, DATE '2021-06-01');

-- R&D
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Hồ Thị Ánh', 'anh.ho@company.vn', 'R&D Manager', 12, DATE '2018-03-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Ngô Văn Bảo', 'bao.ngo@company.vn', 'AI Researcher', 12, DATE '2019-09-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Lê Thị Cẩm', 'cam.le@company.vn', 'Data Scientist', 12, DATE '2020-04-01');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Trần Văn Dũng', 'dung.tran@company.vn', 'ML Engineer', 12, DATE '2021-01-15');
INSERT INTO employees (full_name, email, title, department_id, hire_date) VALUES ('Nguyễn Thị Hà', 'ha.nguyen@company.vn', 'Research Assistant', 12, DATE '2022-03-01');

-- Thêm nhân viên junior / intern để có mạng dày hơn
INSERT INTO employees (full_name, email, title, department_id, hire_date) 
SELECT 'Nhân viên ' || LEVEL, 'nv' || LEVEL || '@company.vn', 
       CASE WHEN MOD(LEVEL,5)=0 THEN 'Senior Dev' 
            WHEN MOD(LEVEL,3)=0 THEN 'Developer' 
            ELSE 'Junior Dev' END,
       2 + MOD(LEVEL,10), DATE '2022-01-01' + LEVEL
FROM dual CONNECT BY LEVEL <= 50;

COMMIT;

-- 3. REPORTS_TO (Hierarchy)
-- CEO
INSERT INTO reports_to (employee_id, manager_id, since_date) VALUES (2, 1, DATE '2016-07-15'); -- Phó TGĐ -> TGĐ
INSERT INTO reports_to (employee_id, manager_id, since_date) VALUES (3, 1, DATE '2017-01-10'); -- GĐ CNTT -> TGĐ
INSERT INTO reports_to (employee_id, manager_id, since_date) VALUES (4, 1, DATE '2017-05-20'); -- GĐ SP -> TGĐ
INSERT INTO reports_to (employee_id, manager_id, since_date) VALUES (5, 1, DATE '2018-02-01'); -- GĐ MKT -> TGĐ

-- Phòng Công nghệ
INSERT INTO reports_to (employee_id, manager_id) VALUES (6, 3);  -- Trưởng Backend -> GĐ CNTT
INSERT INTO reports_to (employee_id, manager_id) VALUES (7, 3);  -- Trưởng Frontend -> GĐ CNTT
INSERT INTO reports_to (employee_id, manager_id) VALUES (8, 6);  -- Tech Lead -> Trưởng Backend
INSERT INTO reports_to (employee_id, manager_id) VALUES (9, 8);  -- Senior BE -> Tech Lead
INSERT INTO reports_to (employee_id, manager_id) VALUES (10, 7); -- Senior FE -> Trưởng FE
INSERT INTO reports_to (employee_id, manager_id) VALUES (11, 9); -- BE Dev -> Senior BE
INSERT INTO reports_to (employee_id, manager_id) VALUES (12, 10);
INSERT INTO reports_to (employee_id, manager_id) VALUES (13, 6); -- DevOps -> Trưởng BE
INSERT INTO reports_to (employee_id, manager_id) VALUES (14, 8);
INSERT INTO reports_to (employee_id, manager_id) VALUES (15, 8);
INSERT INTO reports_to (employee_id, manager_id) VALUES (16, 9);
INSERT INTO reports_to (employee_id, manager_id) VALUES (17, 10);
INSERT INTO reports_to (employee_id, manager_id) VALUES (18, 7);
INSERT INTO reports_to (employee_id, manager_id) VALUES (19, 7);
INSERT INTO reports_to (employee_id, manager_id) VALUES (20, 11);
INSERT INTO reports_to (employee_id, manager_id) VALUES (21, 12);
INSERT INTO reports_to (employee_id, manager_id) VALUES (22, 20);

-- Phòng Sản phẩm
INSERT INTO reports_to (employee_id, manager_id) VALUES (23, 4);
INSERT INTO reports_to (employee_id, manager_id) VALUES (24, 23);
INSERT INTO reports_to (employee_id, manager_id) VALUES (25, 23);
INSERT INTO reports_to (employee_id, manager_id) VALUES (26, 24);
INSERT INTO reports_to (employee_id, manager_id) VALUES (27, 24);

-- Phòng Marketing
INSERT INTO reports_to (employee_id, manager_id) VALUES (28, 5);
INSERT INTO reports_to (employee_id, manager_id) VALUES (29, 28);
INSERT INTO reports_to (employee_id, manager_id) VALUES (30, 28);
INSERT INTO reports_to (employee_id, manager_id) VALUES (31, 29);
INSERT INTO reports_to (employee_id, manager_id) VALUES (32, 29);

-- HR
INSERT INTO reports_to (employee_id, manager_id) VALUES (33, 2);
INSERT INTO reports_to (employee_id, manager_id) VALUES (34, 33);
INSERT INTO reports_to (employee_id, manager_id) VALUES (35, 33);
INSERT INTO reports_to (employee_id, manager_id) VALUES (36, 33);

-- Tài chính
INSERT INTO reports_to (employee_id, manager_id) VALUES (37, 2);
INSERT INTO reports_to (employee_id, manager_id) VALUES (38, 37);
INSERT INTO reports_to (employee_id, manager_id) VALUES (39, 38);
INSERT INTO reports_to (employee_id, manager_id) VALUES (40, 38);

-- Kinh doanh
INSERT INTO reports_to (employee_id, manager_id) VALUES (41, 2);
INSERT INTO reports_to (employee_id, manager_id) VALUES (42, 41);
INSERT INTO reports_to (employee_id, manager_id) VALUES (43, 42);
INSERT INTO reports_to (employee_id, manager_id) VALUES (44, 42);
INSERT INTO reports_to (employee_id, manager_id) VALUES (45, 42);

-- CSKH
INSERT INTO reports_to (employee_id, manager_id) VALUES (46, 2);
INSERT INTO reports_to (employee_id, manager_id) VALUES (47, 46);
INSERT INTO reports_to (employee_id, manager_id) VALUES (48, 47);
INSERT INTO reports_to (employee_id, manager_id) VALUES (49, 47);

-- Chi nhánh
INSERT INTO reports_to (employee_id, manager_id) VALUES (50, 2); -- GĐ HN -> Phó TGĐ
INSERT INTO reports_to (employee_id, manager_id) VALUES (51, 50);
INSERT INTO reports_to (employee_id, manager_id) VALUES (52, 50);
INSERT INTO reports_to (employee_id, manager_id) VALUES (53, 52);
INSERT INTO reports_to (employee_id, manager_id) VALUES (54, 51);
INSERT INTO reports_to (employee_id, manager_id) VALUES (55, 51);

INSERT INTO reports_to (employee_id, manager_id) VALUES (56, 2);
INSERT INTO reports_to (employee_id, manager_id) VALUES (57, 56);
INSERT INTO reports_to (employee_id, manager_id) VALUES (58, 56);
INSERT INTO reports_to (employee_id, manager_id) VALUES (59, 56);

INSERT INTO reports_to (employee_id, manager_id) VALUES (60, 2);
INSERT INTO reports_to (employee_id, manager_id) VALUES (61, 60);
INSERT INTO reports_to (employee_id, manager_id) VALUES (62, 61);

-- R&D
INSERT INTO reports_to (employee_id, manager_id) VALUES (63, 3);
INSERT INTO reports_to (employee_id, manager_id) VALUES (64, 63);
INSERT INTO reports_to (employee_id, manager_id) VALUES (65, 63);
INSERT INTO reports_to (employee_id, manager_id) VALUES (66, 64);
INSERT INTO reports_to (employee_id, manager_id) VALUES (67, 65);

COMMIT;

-- 4. PROJECTS
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Nền tảng Core Banking 2.0', 'Nâng cấp hệ thống core', DATE '2024-01-15', 'ACTIVE', 2);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Mobile App Khách hàng', 'App mobile cho khách hàng cá nhân', DATE '2024-03-01', 'ACTIVE', 2);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('AI Chatbot CSKH', 'Chatbot hỗ trợ khách hàng 24/7', DATE '2024-02-01', 'ACTIVE', 12);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Hệ thống CRM mới', 'CRM tích hợp đa kênh', DATE '2023-11-01', 'ACTIVE', 3);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Digital Marketing 2025', 'Chiến dịch marketing số', DATE '2025-01-01', 'PLANNING', 4);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Nâng cấp Data Warehouse', 'Xây dựng DWH mới', DATE '2024-06-01', 'ACTIVE', 2);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Portal Nhân sự nội bộ', 'Self-service HR portal', DATE '2024-04-01', 'ACTIVE', 5);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Hệ thống chấm công AI', 'Face recognition attendance', DATE '2024-08-01', 'ACTIVE', 12);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('E-commerce Platform', 'Sàn thương mại điện tử nội bộ', DATE '2023-09-01', 'COMPLETED', 3);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Security Compliance 2025', 'Tuân thủ bảo mật', DATE '2025-02-01', 'PLANNING', 2);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Chi nhánh số Hà Nội', 'Chuyển đổi số chi nhánh HN', DATE '2024-05-01', 'ACTIVE', 9);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Chi nhánh số Đà Nẵng', 'Chuyển đổi số chi nhánh DN', DATE '2024-07-01', 'ACTIVE', 10);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('API Gateway nội bộ', 'API management platform', DATE '2024-01-01', 'ACTIVE', 2);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Knowledge Base', 'Cơ sở tri thức nội bộ', DATE '2024-09-01', 'ACTIVE', 5);
INSERT INTO projects (project_name, description, start_date, status, department_id) VALUES 
('Performance Review System', 'Hệ thống đánh giá hiệu suất', DATE '2024-10-01', 'PLANNING', 5);

COMMIT;

-- 5. PROJECT_MEMBERS (tạo mạng đồng đội)
-- Project 1: Core Banking
INSERT INTO project_members (employee_id, project_id, role) VALUES (3,1,'SPONSOR');
INSERT INTO project_members (employee_id, project_id, role) VALUES (6,1,'LEAD');
INSERT INTO project_members (employee_id, project_id, role) VALUES (8,1,'TECH_LEAD');
INSERT INTO project_members (employee_id, project_id, role) VALUES (9,1,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (11,1,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (13,1,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (15,1,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (16,1,'MEMBER');

-- Project 2: Mobile App
INSERT INTO project_members (employee_id, project_id, role) VALUES (7,2,'LEAD');
INSERT INTO project_members (employee_id, project_id, role) VALUES (10,2,'TECH_LEAD');
INSERT INTO project_members (employee_id, project_id, role) VALUES (12,2,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (17,2,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (18,2,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (19,2,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (23,2,'PRODUCT');

-- Project 3: AI Chatbot
INSERT INTO project_members (employee_id, project_id, role) VALUES (63,3,'LEAD');
INSERT INTO project_members (employee_id, project_id, role) VALUES (64,3,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (65,3,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (66,3,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (8,3,'ADVISOR');
INSERT INTO project_members (employee_id, project_id, role) VALUES (15,3,'MEMBER');

-- Project 4: CRM
INSERT INTO project_members (employee_id, project_id, role) VALUES (23,4,'LEAD');
INSERT INTO project_members (employee_id, project_id, role) VALUES (24,4,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (25,4,'MEMBER');
INSERT INTO project_members (employee_id, project_id, role) VALUES (9,4,'TECH');
INSERT INTO project_members (employee_id, project_id, role) VALUES (11,4,'TECH');

-- Thêm thành viên cho các project khác (rút gọn)
INSERT INTO project_members (employee_id, project_id, role)
SELECT e.employee_id, p.project_id, 'MEMBER'
FROM employees e, projects p
WHERE p.project_id BETWEEN 5 AND 15
  AND MOD(e.employee_id + p.project_id, 7) = 0
  AND e.employee_id <= 70;

COMMIT;

-- 6. KNOWS (Social connections)
-- Mentor relationships
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (9, 8, 'MENTOR', 4.5);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (11, 9, 'MENTOR', 4.0);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (20, 11, 'MENTOR', 3.5);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (10, 7, 'MENTOR', 4.2);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (12, 10, 'MENTOR', 3.8);

-- Friends / Colleagues across teams
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (8, 23, 'FRIEND', 3.0);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (9, 24, 'COLLEAGUE', 2.5);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (15, 64, 'COLLEAGUE', 3.0);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (6, 63, 'FRIEND', 3.5);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (3, 63, 'COLLEAGUE', 4.0);

-- Cross branch
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (52, 8, 'COLLEAGUE', 2.8);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (53, 11, 'FRIEND', 2.5);
INSERT INTO knows (from_emp, to_emp, connection_type, strength) VALUES (58, 12, 'COLLEAGUE', 2.0);

-- Tự động tạo một số quan hệ COLLEAGUE trong cùng phòng
INSERT INTO knows (from_emp, to_emp, connection_type, strength)
SELECT e1.employee_id, e2.employee_id, 'COLLEAGUE', 1.5
FROM employees e1
JOIN employees e2 ON e1.department_id = e2.department_id
                 AND e1.employee_id < e2.employee_id
                 AND MOD(e1.employee_id + e2.employee_id, 5) = 0
WHERE e1.employee_id <= 70 AND e2.employee_id <= 70
  AND NOT EXISTS (
    SELECT 1 FROM knows k WHERE k.from_emp = e1.employee_id AND k.to_emp = e2.employee_id
  );

COMMIT;

PROMPT ===== SAMPLE DATA LOADED SUCCESSFULLY =====
PROMPT Employees: 
SELECT COUNT(*) AS emp_count FROM employees;
PROMPT Projects: 
SELECT COUNT(*) AS proj_count FROM projects;
PROMPT Project Members: 
SELECT COUNT(*) AS pm_count FROM project_members;
PROMPT Knows relations: 
SELECT COUNT(*) AS knows_count FROM knows;
PROMPT Reports_to: 
SELECT COUNT(*) AS reports_count FROM reports_to;
