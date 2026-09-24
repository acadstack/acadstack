import { createRouter, createWebHashHistory } from 'vue-router'

// 1. Define/import route components.
import Login from "../components/Login.vue";
import Help from "../components/Help.vue";
import Home from "../components/Home.vue";
import PasswordReset from "../components/PasswordReset.vue";
import UserDetails from "../components/UserDetails.vue";
import UserSearch from "../components/UserSearch.vue";
import KnownFaceZipUpload from "../components/KnownFaceZipUpload.vue";
import AttendanceSearch from "../components/AttendanceSearch.vue";
import AttendanceDetails from "../components/AttendanceDetails.vue";
import MarkAttendance from "../components/MarkAttendance.vue";

import StudentDetails from "../components/StudentDetails.vue";
import StudentSearch from "../components/StudentSearch.vue";
import CourseSearch from "../components/CourseSearch.vue";
import CourseDetails from "../components/CourseDetails.vue";
import CourseDetailsPrintable from "../components/CourseDetailsPrintable.vue";
import InstructorSearch from "../components/InstructorSearch.vue";
import InstructorDetails from "../components/InstructorDetails.vue";
import CourseOfferingSearch from "../components/CourseOfferingSearch.vue";
import CourseOfferingDetails from "../components/CourseOfferingDetails.vue";
import CourseEnrollmentDetails from "../components/CourseEnrollmentDetails.vue";
import GradesUpload from "../components/GradesUpload.vue";
import EarnedCreditsReport from "../components/EarnedCreditsReport.vue";
import AddAcademicDates from "../components/AddAcademicDates.vue";
import PendingTasks from "../components/PendingTasks.vue";
import AddUsers from "../components/AddUsers.vue";
import AddCourses from "../components/AddCourses.vue";
import BulkEnrolCourse from "../components/BulkEnrolCourse.vue";
import CreateFeedbackForm from "../components/CreateFeedbackForm.vue";
import CourseInstructorFeedback from "../components/CourseInstructorFeedback.vue";
import CreditsCheckReport from "../components/CreditsCheckReport.vue";
import GenerateSemesterGrade from "../components/GenerateSemesterGrade.vue";
import ViewInstructorFeedback from "../components/ViewInstructorFeedback.vue";
import CourseSlotTiming from "../components/CourseSlotTiming.vue";
import RegistrationFeesDetails from "../components/RegistrationFeesDetails.vue";
import FeesPaymentReport from "../components/FeesPaymentReport.vue";
import GenerateCourseEnrolments from "../components/GenerateCourseEnrolments.vue";
import FeedbackStats from "../components/FeedbackStats.vue";
import SlotWiseCourses from "../components/SlotWiseCourses.vue";
import GenCreditsData from "../components/GenCreditsData.vue";
import GradeDistribution from "../components/GradeDistribution.vue";
import CgpaSgpa from "../components/CgpaSgpa.vue";
import ManageBatchAdvisors from "../components/ManageBatchAdvisors.vue";
import DeptwiseAverage from "../components/DeptwiseAverage.vue";
import CourseWiseFacultyScore from "../components/CourseWiseFacultyScore.vue";
import QueWiseFacFeedbkScore from "../components/QueWiseFacFeedbkScore.vue";
import StudentStrength from "../components/StudentStrength.vue";
import DcSearch from "../components/DcSearch.vue";
import DcDetails from "../components/DcDetails.vue";
import GradesStatus from "../components/GradesStatus.vue";
import BulkDownloadGradeSheet from "../components/BulkDownloadGradeSheet.vue";
import GenerateDegreeCertifcate from "../components/GenerateDegreeCertifcate.vue";
import PhdProgressReport from "../components/PhdProgressReport.vue";
import ConsolidatedGradeSheet from "../components/ConsolidatedGradeSheet.vue";
import MyPhdProgressReports from "../components/MyPhdProgressReports.vue";
import OnlineFeesSubmission from "../components/OnlineFeesSubmission.vue";
import KnownFaceUpload from "../components/KnownFaceUpload.vue";
import CourseAttendance from "../components/CourseAttendance.vue"
import SystemSettingsAdmin from "../components/SystemSettingsAdmin.vue"
import AcademicPolicyAdmin from "../components/AcademicPolicyAdmin.vue"
import ConfigTransfer from "../components/ConfigTransfer.vue"

// 2. Define routes
const appRoutes = [{
  name: 'login',
  path: '/login',
  component: Login
},
{
  name: 'pass.reset',
  path: '/pass.reset',
  component: PasswordReset
},
{
  path: '/help',
  component: Help
},
{
  path: '/',
  component: Home
},
{
  name: "add.users",
  path: '/add.users',
  component: AddUsers
},
{
  name: "user.find",
  path: '/user.find',
  component: UserSearch
},
{
  name: "user.detail",
  path: '/user.detail/:id?',
  component: UserDetails
},
{
  name: 'kf.zip.upload',
  path: '/kf.zip.upload',
  component: KnownFaceZipUpload
},
{
  name: 'att.find',
  path: '/att.find',
  component: AttendanceSearch
},
{
  name: 'att.detail',
  path: '/att.detail/:id?',
  component: AttendanceDetails
},
{
  name: 'att.mark',
  path: '/att.mark',
  component: MarkAttendance
},
{
  name: 'std.find',
  path: '/std.find',
  component: StudentSearch
},
{
  name: 'std.detail',
  path: '/std.detail/:id?',
  component: StudentDetails
},
{
  name: 'courses.add',
  path: '/courses.add',
  component: AddCourses
},
{
  name: 'cour.find',
  path: '/cour.find',
  component: CourseSearch
},
{
  name: 'course',
  path: '/cour.detail/:id?',
  component: CourseDetails
},
{
  name: 'cour.print',
  path: '/cour.print/:id?',
  component: CourseDetailsPrintable
},
{
  name: 'ins.find',
  path: '/ins.find',
  component: InstructorSearch
},
{
  name: 'ins.detail',
  path: '/ins.detail/:id?',
  component: InstructorDetails
},
{
  name: 'co.find',
  path: '/co.find',
  component: CourseOfferingSearch
},
{
  name: 'co.detail',
  path: '/co.detail/:id?',
  component: CourseOfferingDetails
},
{
  name: 'coe.detail',
  path: '/coe.detail/:id?',
  component: CourseEnrollmentDetails
},
{
  name: 'grades.upload',
  path: '/grades.upload',
  component: GradesUpload
},
{
  name: 'credits.earned',
  path: '/credits.earned',
  component: EarnedCreditsReport
},
{
  name: 'add.dates',
  path: '/add.dates',
  component: AddAcademicDates
},
{
  name: 'my.cour',
  path: '/my.cour',
  component: CourseSearch
},
{
  name: 'my.coff',
  path: '/my.coff',
  component: CourseOfferingSearch
},
{
  name: 'pending.tasks',
  path: '/pending.tasks',
  component: PendingTasks
},
{
  name: 'my.actions',
  path: '/my.actions',
  component: PendingTasks
},
{
  name: 'co.bulkenrol',
  path: '/co.bulkenrol',
  component: BulkEnrolCourse
},
{
  name: 'create.form',
  path: '/create.form',
  component: CreateFeedbackForm
},
{
  name: 'co.feedback',
  path: '/co.feedback',
  component: CourseInstructorFeedback
},
{
  name: 'feedback.stats',
  path: '/feedback.stats',
  component: FeedbackStats
},
{
  name: 'credits.check',
  path: '/credits.check',
  component: CreditsCheckReport
},
{  
  name: 'course.enrolments',
  path: '/course.enrolments',
  component: GenerateCourseEnrolments
},
{
  name: 'semester.grade',
  path: '/semester.grade',
  component: GenerateSemesterGrade
},
{
  name: 'view.insfb',
  path: '/view.insfb/:co_id/:user_id/:fb_type',
  component: ViewInstructorFeedback
},
{
  name: 'edit.slots',
  path: '/edit.slots',
  component: CourseSlotTiming
},
{
  name: 'std.fees',
  path: '/std.fees/:user_id?',
  component: RegistrationFeesDetails
},
{
  name: 'fees.report',
  path: '/fees.report',
  component: FeesPaymentReport
},
{
  name: 'swc',
  path: '/swc',
  component: SlotWiseCourses
},
{
  name: 'gcd',
  path: '/gcd',
  component: GenCreditsData
},
{
  name: 'grade-dist',
  path: '/grade.dist',
  component: GradeDistribution
},
{
  name: 'cgpa-sgpa',
  path: '/cgpa.sgpa',
  component: CgpaSgpa
},
{
  name: 'mba',
  path: '/mba',
  component: ManageBatchAdvisors
},
{
  name: 'dept.wiseavg',
  path: '/dept.wiseavg',
  component:  DeptwiseAverage
},
{
  name: 'coursewise.facultyscore',
  path: '/coursewise.facultyscore',
  component:  CourseWiseFacultyScore
},
{
  name: 'queswise.facscore',
  path: '/queswise.facscore',
  component:  QueWiseFacFeedbkScore
},
{
  name: 'stu.strength',
  path: '/stu.strength',
  component:  StudentStrength
},
{
  name: 'dc.form',
  path: '/dc.form/:stu_id?',
  component:  DcDetails
},
{
  name: 'dc.find',
  path: '/dc.find',
  component:  DcSearch
},
{
  name: 'grades.status',
  path: '/grades.status',
  component:  GradesStatus
},
{
  name: 'gs.bulk',
  path: '/gs.bulk',
  component:  BulkDownloadGradeSheet
},
{
  name: 'degree.cert',
  path: '/degree.cert',
  component:  GenerateDegreeCertifcate
},
{
  name: 'ppr',
  path: '/ppr/:ppr_id?',
  component:  PhdProgressReport
},
{
  name: 'consolid.cert',
  path: '/consolid.cert',
  component:  ConsolidatedGradeSheet
},
{
  name: 'myppr',
  path: '/myppr',
  component:  MyPhdProgressReports
},
{
  name: 'feessub.online',
  path: '/feessub.online',
  component: OnlineFeesSubmission
},
{
  name: 'myphoto',
  path: '/myphoto',
  component: KnownFaceUpload
},
{
  name: 'CourseAttendance',
  path: '/co.att/:co_id/:att_dt',
  component: CourseAttendance
},
{
  name: 'admin.settings',
  path: '/admin.settings',
  component: SystemSettingsAdmin
},
{
  name: 'admin.policy',
  path: '/admin.policy',
  component: AcademicPolicyAdmin
},
{
  name: 'admin.config_transfer',
  path: '/admin.config_transfer',
  component: ConfigTransfer
}
]

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: appRoutes
})

export default router
