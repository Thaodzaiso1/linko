-- Verify Oracle 23ai components. Execute as the schema that owns all 7 tables.
SET SERVEROUTPUT ON
-- PRODUCT_COMPONENT_VERSION avoids V$VERSION grants needed by restricted schema accounts.
SELECT product, version FROM product_component_version WHERE product LIKE 'Oracle%';
SELECT object_name, object_type, status FROM user_objects
 WHERE object_name IN ('PKG_SOCIAL_NETWORK','TRG_AUTO_TEAMMATE','TRG_AUDIT_KNOWS','TRG_AUDIT_EMPLOYEES','TRG_AUDIT_DEPARTMENTS','TRG_AUDIT_PROJECTS','TRG_AUDIT_PROJECT_MEMBERS','TRG_AUDIT_REPORTS_TO','ENTERPRISE_SOCIAL_GRAPH')
 ORDER BY object_type, object_name;
SELECT name, type, line, position, text FROM user_errors ORDER BY name, sequence;
SELECT COUNT(*) AS employees FROM employees;
SELECT COUNT(*) AS projects FROM projects;
SELECT COUNT(*) AS relations FROM knows;
SELECT * FROM GRAPH_TABLE (enterprise_social_graph
 MATCH (a IS Employee)-[e IS ReportsTo]->(b IS Employee)
 WHERE a.employee_id = 20
 COLUMNS (a.employee_id AS employee_id, b.employee_id AS manager_id));
SELECT pkg_social_network.find_shortest_path_length(3,1,1) AS shortest_hops FROM dual;
