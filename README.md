Of course. Here is the user story document transformed into a more testing-friendly format, focusing on clear, actionable features with defined testing scenarios.

The key changes are:
*   **Restructured as "Features"** instead of "User Stories".
*   **Added a "Testing Focus"** section for each feature, outlining the core functionality to verify.
*   **Defined "Test Scenarios"** with clear steps, expected results, and edge cases.
*   **Standardized the format** for easy consumption by QA teams and automation scripts.

---

# 🏫 School Management System - Testing-Focused Feature Specification

## 👑 Super Administrator

### ⚙️ Feature 1.1: System Configuration Management
*   **Testing Focus:** Verify that global system settings (academic, financial, security, UI) can be modified and changes are applied universally and audited.
*   **Test Scenarios:**
    1.  **Scenario:** Modify a global setting (e.g., default language, date format).
        *   **Steps:** Log in as Super Admin -> Navigate to System Config -> Change a setting -> Save -> Log in to a different school instance.
        *   **Expected Result:** The changed setting is reflected across all school instances.
        *   **Edge Case:** Attempt to save an invalid configuration value (e.g., a negative number for a positive-only field).
    2.  **Scenario:** Verify audit trail for configuration changes.
        *   **Steps:** Make a configuration change -> Navigate to Audit Logs -> Filter for configuration events.
        *   **Expected Result:** A new audit log entry details the change, including user, timestamp, old value, and new value.

### 🏫 Feature 1.2: Multi-Institution Management
*   **Testing Focus:** Verify the creation, configuration, and data isolation of multiple school instances.
*   **Test Scenarios:**
    1.  **Scenario:** Create a new school instance.
        *   **Steps:** Log in as Super Admin -> Navigate to Institution Management -> Create New -> Fill in required details (name, code, type, capacity) -> Save.
        *   **Expected Result:** The new institution appears in the list and can be selected by assigned administrators.
        *   **Edge Case:** Attempt to create an institution with a duplicate code.
    2.  **Scenario:** Test data isolation between institutions.
        *   **Steps:** Create two institutions, A and B -> In Institution A, create a student -> Switch to Institution B's context and search for the student created in A.
        *   **Expected Result:** The student from Institution A is not visible or accessible in Institution B.

### 🛡️ Feature 1.3: User Role Hierarchy Management
*   **Testing Focus:** Verify that roles can be created and modified with specific permission levels, and role assignments are tracked.
*   **Test Scenarios:**
    1.  **Scenario:** Create a new custom role.
        *   **Steps:** Log in as Super Admin -> Navigate to Role Management -> Create New Role -> Define a permission level (e.g., 75) and assign specific permissions (e.g., "Can view finances", "Cannot delete users") -> Save.
        *   **Expected Result:** The new role is available for assignment to users.
        *   **Edge Case:** Assign a user a role with a higher permission level than their existing role and verify the new permissions take effect immediately.
    2.  **Scenario:** Audit role assignment.
        *   **Steps:** Assign a new role to a user -> Check the `UserRoleActivity` log.
        *   **Expected Result:** The log shows the user who made the assignment, the target user, the role assigned, and the timestamp.

---

## 👨‍💼 School Administrator

### 👥 Feature 2.1: Staff Recruitment & Management
*   **Testing Focus:** Verify the complete workflow from receiving a `StaffApplication` to generating an employee ID and creating a staff profile.
*   **Test Scenarios:**
    1.  **Scenario:** Process a staff application through its stages.
        *   **Steps:** Log in as School Admin -> Navigate to Staff Applications -> Open a new application -> Move it through stages (e.g., "Review" -> "Interview" -> "Approved") -> Upon final approval, check if a staff profile is auto-created with a unique employee ID from `SequenceGenerator`.
        *   **Expected Result:** The application progresses correctly, and a new staff member is added to the system with a unique ID.
        *   **Edge Case:** Reject an application and verify the workflow ends appropriately without creating a profile.

### 💰 Feature 2.2: Financial Management & Billing
*   **Testing Focus:** Verify the setup of fee structures, invoice generation, and payment tracking.
*   **Test Scenarios:**
    1.  **Scenario:** Create and apply a `FeeStructure`.
        *   **Steps:** Log in as School Admin -> Navigate to Finance -> Fee Structures -> Create a new fee structure for "Grade 10" -> Assign it to a student -> Navigate to the student's profile.
        *   **Expected Result:** An `Invoice` is generated for the student based on the new fee structure.
        *   **Edge Case:** Modify a fee structure after invoices are generated and verify that existing invoices are not affected, but new ones are.

---

## 📚 Principal

### 📊 Feature 3.1: Academic Performance Monitoring
*   **Testing Focus:** Verify access to and accuracy of academic reports and analytics.
*   **Test Scenarios:**
    1.  **Scenario:** Generate a class performance report.
        *   **Steps:** Log in as Principal -> Navigate to Analytics -> Academic Performance -> Select a class and academic session -> Generate Report.
        *   **Expected Result:** A report displays `Result` and `ReportCard` data, showing averages, trends, and comparisons.
        *   **Edge Case:** Run a report for a class with no assessment data; the system should handle this gracefully (e.g., show "No Data" message).

### 👨‍🏫 Feature 3.2: Teacher Management & Support
*   **Testing Focus:** Verify the ability to oversee teacher assignments and access performance metrics.
*   **Test Scenarios:**
    1.  **Scenario:** Review a teacher's workload.
        *   **Steps:** Log in as Principal -> Navigate to Staff -> Teachers -> Select a teacher -> View "Teaching Load" or "Assignments".
        *   **Expected Result:** The view displays all `SubjectAssignment`s and `Class`es taught by the teacher, including a summary of total periods.
        *   **Edge Case:** Assign a teacher to a new class that creates a scheduling conflict; the system should warn the user.

---

## 👨‍🏫 Teacher

### ✅ Feature 4.1: Classroom Attendance Management
*   **Testing Focus:** Verify accurate recording of `DailyAttendance` and `PeriodAttendance`.
*   **Test Scenarios:**
    1.  **Scenario:** Take attendance for a class.
        *   **Steps:** Log in as Teacher -> Navigate to My Classes -> Select a class -> Click "Take Attendance" -> Mark students as Present/Absent/Late -> Save.
        *   **Expected Result:** The attendance is saved. The `AttendanceSummary` for the class and individual students is updated.
        *   **Edge Case:** Try to submit attendance without marking any students; the system should prompt the user or prevent submission.

### 📝 Feature 4.2: Assessment & Grading
*   **Testing Focus:** Verify the creation of assessments, entry of marks, and correct application of the `GradingSystem`.
*   **Test Scenarios:**
    1.  **Scenario:** Create an assignment and grade students.
        *   **Steps:** Log in as Teacher -> Navigate to Assessments -> Create Assignment -> Enter details (title, max marks, due date) -> Save -> Enter `Marks` for students -> Submit.
        *   **Expected Result:** The assignment appears in the teacher's and students' portals. The entered marks are reflected in the students' `AcademicRecord` and the correct grade from the `GradingSystem` is applied.
        *   **Edge Case:** Enter a mark that exceeds the maximum allowed marks; the system should show a validation error.

---

## 🎓 Student

### 📅 Feature 5.1: Academic Dashboard & Schedule
*   **Testing Focus:** Verify students see a personalized, accurate timetable.
*   **Test Scenarios:**
    1.  **Scenario:** View personalized timetable.
        *   **Steps:** Log in as Student -> Navigate to Dashboard or My Schedule.
        *   **Expected Result:** The `Timetable` displays only the classes and subjects for which the student is enrolled, including `Room` and teacher information.
        *   **Edge Case:** View the timetable on a day with a scheduled `Holiday`; the holiday should be clearly indicated.

### 📊 Feature 5.2: Performance Tracking
*   **Testing Focus:** Verify students can access their own grades and results.
*   **Test Scenarios:**
    1.  **Scenario:** Check assessment results.
        *   **Steps:** Log in as Student -> Navigate to Academics -> My Grades -> Select a subject.
        *   **Expected Result:** The student can see all their `Marks` for `Assignment`s and `Exam`s, their `Result`,
        *   **Edge Case:** Access grades for an assessment before the teacher has published them; the grades should not be visible.

---

## 👨‍👩‍👧‍👦 Parent

### 📈 Feature 6.1: Child Progress Monitoring
*   **Testing Focus:** Verify parents can view their child's attendance and academic reports.
*   **Test Scenarios:**
    1.  **Scenario:** Monitor child's attendance and grades.
        *   **Steps:** Log in as Parent -> Select a child from the profile switcher -> View Dashboard.
        *   **Expected Result:** The dashboard shows a summary of the child's recent `AttendanceSummary` and `ReportCard`/assessment results.
        *   **Edge Case:** As a parent with multiple children, switch between profiles and verify the data is isolated and correct for each child.

### 💰 Feature 6.2: Fee Management & Payments
*   **Testing Focus:** Verify parents can view invoices and make payments.
*   **Test Scenarios:**
    1.  **Scenario:** Pay an outstanding fee invoice.
        *   **Steps:** Log in as Parent -> Navigate to Finance -> Invoices -> Select an unpaid `Invoice` -> Click "Pay" -> Complete the payment flow in a test gateway.
        *   **Expected Result:** The invoice status updates to "Paid", and a `Payment` record is created. The parent receives a confirmation message.
        *   **Edge Case:** Attempt to pay an invoice that is already paid; the system should prevent the payment.

---

## 👨‍💻 Support Staff

### 🛠️ Feature 7.1: User Support & Issue Resolution
*   **Testing Focus:** Verify the process of receiving and resolving user support tickets.
*   **Test Scenarios:**
    1.  **Scenario:** Resolve a user-submitted ticket.
        *   **Steps:** Log in as Support Staff -> Navigate to Help Desk -> Open a new `ContactSubmission` -> Change status from "Open" to "In Progress" to "Resolved" -> Add internal notes.
        *   **Expected Result:** The ticket's status and history are updated. The user (if configured) receives status notifications.
        *   **Edge Case:** Try to close a ticket without adding a resolution note (if required by policy); the system should enforce this rule.

### 📚 Feature 7.2: Knowledge Base Management
*   **Testing Focus:** Verify creation and management of `HelpCenterArticle`.
*   **Test Scenarios:**
    1.  **Scenario:** Create and publish a new help article.
        *   **Steps:** Log in as Support Staff -> Navigate to Knowledge Base -> Create Article -> Fill in title, content, assign `Category` and `Tag`s -> Set status to "Published" -> Save.
        *   **Expected Result:** The article becomes visible to the intended user roles in the help center. It is searchable via its title and tags.
        *   **Edge Case:** Create an article with a duplicate title; the system should allow it or handle it appropriately (e.g., with a unique slug).

---

## 🚌 Transport Manager

### 🚗 Feature 8.1: Fleet Management
*   **Testing Focus:** Verify management of `Vehicle` records and `MaintenanceRecord`s.
*   **Test Scenarios:**
    1.  **Scenario:** Add a new vehicle and schedule maintenance.
        *   **Steps:** Log in as Transport Manager -> Navigate to Fleet -> Add Vehicle -> Enter details (plate, capacity, insurance) -> Schedule a `MaintenanceRecord` for the vehicle.
        *   **Expected Result:** The vehicle is added to the fleet. The maintenance record appears in the vehicle's history and triggers reminders as the date approaches.
        *   **Edge Case:** Attempt to assign a vehicle to a route while it is scheduled for maintenance; the system should warn about the conflict.

### 🗺️ Feature 8.2: Route Planning & Optimization
*   **Testing Focus:** Verify creation of `Route` with `RouteStop`s and assignment to vehicles and students.
*   **Test Scenarios:**
    1.  **Scenario:** Create a new bus route and assign students.
        *   **Steps:** Log in as Transport Manager -> Navigate to Routes -> Create Route -> Add multiple `RouteStop`s in sequence -> Assign a `Driver` and `Vehicle` -> Use "Assign Students" to create `TransportAllocation`s.
        *   **Expected Result:** The route is saved. Assigned students and their parents can see the route and stop details in their portals.
        *   **Edge Case:** Assign a student to a route that is already at vehicle capacity; the system should prevent the assignment or show a warning.

---

## 🏠 Hostel Warden

### 🏢 Feature 9.1: Hostel Facility Management
*   **Testing Focus:** Verify management of `Hostel`, `Room`, and `Bed` assignments.
*   **Test Scenarios:**
    1.  **Scenario:** Allocate a student to a hostel bed.
        *   **Steps:** Log in as Hostel Warden -> Navigate to Hostel Management -> Select a `Hostel` -> Select a `Room` -> Assign a student to an available `Bed` via `HostelAllocation`.
        *   **Expected Result:** The bed's status changes to "Occupied". The student's profile is updated to show their hostel assignment.
        *   **Edge Case:** Try to assign two students to the same bed; the system must prevent this.

### 🔧 Feature 9.2: Maintenance & Facility Issues
*   **Testing Focus:** Verify the workflow for handling `MaintenanceRequest`s.
*   **Test Scenarios:**
    1.  **Scenario:** Process a maintenance request from a student.
        *   **Steps:** (As a Student) Submit a `MaintenanceRequest` for a room issue -> (As Warden) Log in -> Navigate to Maintenance -> View the new request -> Assign it for repair -> Mark as "Completed".
        *   **Expected Result:** The request moves through the statuses correctly. The student receives notifications about the status updates.
        *   **Edge Case:** Attempt to close a request without assigning a resolution; the system should require a completion note.

---

## 📖 Librarian

### 📚 Feature 10.1: Library Collection Management
*   **Testing Focus:** Verify the process of adding `Book` records and managing `BookCopy` inventory.
*   **Test Scenarios:**
    1.  **Scenario:** Add a new book to the library catalog.
        *   **Steps:** Log in as Librarian -> Navigate to Catalog -> Add Book -> Enter metadata (title, author, ISBN, `BookCategory`) -> Add multiple `BookCopy` entries for the same title.
        *   **Expected Result:** The book appears in the public catalog. The number of available copies is correctly calculated.
        *   **Edge Case:** Add a book with a duplicate ISBN; the system should suggest merging with the existing record or handle duplicates per policy.

### 🔄 Feature 10.2: Circulation Management
*   **Testing Focus:** Verify the book borrowing, return, and reservation process.
*   **Test Scenarios:**
    1.  **Scenario:** Issue a book to a student.
        *   **Steps:** Log in as Librarian -> Navigate to Circulation -> Find a student (`LibraryMember`) -> Scan/select an available `BookCopy` -> Click "Borrow" to create a `BorrowRecord`.
        *   **Expected Result:** The `BorrowRecord` is created with a due date. The book's status changes to "Checked Out". The student's borrowing count increases.
        *   **Edge Case:** Attempt to issue a book to a student who has overdue books or has reached their borrowing limit; the system should block the transaction.

---

## ⚽ Extracurricular Activities Coordinator

### 📅 Feature 11.1: Activity Planning & Scheduling
*   **Testing Focus:** Verify creation and scheduling of `Activity` records.
*   **Test Scenarios:**
    1.  **Scenario:** Create a new sports activity.
        *   **Steps:** Log in as Coordinator -> Navigate to Activities -> Create Activity -> Fill in details (name, category "Sports", description) -> Set a recurring schedule -> Assign a venue and `ActivityCoach`.
        *   **Expected Result:** The activity is published and becomes visible for student registration. The schedule appears in the assigned coach's timetable.
        *   **Edge Case:** Schedule two activities in the same venue at the same time; the system should warn about the double-booking.

### 👥 Feature 11.2: Student Registration & Enrollment
*   **Testing Focus:** Verify the `ActivityEnrollment` process with capacity limits.
*   **Test Scenarios:**
    1.  **Scenario:** Enroll students in an activity with a capacity limit.
        *   **Steps:** (As Coordinator) Create an activity with a capacity of 10 -> (As multiple Students) Attempt to enroll -> (As Coordinator) Monitor enrollment.
        *   **Expected Result:** The first 10 students enroll successfully. The 11th student is either blocked or added to a waitlist, depending on system configuration.
        *   **Edge Case:** A student drops out of a full activity; verify the waitlist (if enabled) automatically offers the spot to the next student.

