import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import axios from 'axios'

const app = createApp(App)
app.config.globalProperties.$http = axios
app.use(router)

app.mixin({
    methods: {
        async doHttp(isGet, url, postData, onOk, onError) {
            let vm = this;
            try {
                const res = isGet ? await vm.$http.get(url) : await vm.$http.post(url, postData);
                if (res.data.status == "OK") {
                    onOk(res.data.body)
                } else {
                    onError(res.data.body)
                }
            } catch (error) {
                console.log(error);
                vm.setStatusMessage("Error occurred when contacting the server.");
            }
        },
        setStaticData(sd) {
            this.$root.staticData = sd;
        },
        setStatusMessage(msg) {
            this.$root.statusMessage = msg;
        },
        setCurrentUser(user) {
            this.$root.user = user;
        },
        hasPermission(name) {
            // The backend sends the logged-in user's permission set
            // (permissions.py's permissions_for_role()) alongside nav in
            // the login/current_user response -- see api_auth.login()
            // and api_common.get_current_user_and_nav().
            const perms = this.$root.user && this.$root.user.permissions;
            return !!perms && perms.includes(name);
        },
        labelFor(items, key) {
            if (!items || !key) return "--";
            let obj = items.find(elm => elm.id == key);
            if (obj) {
                return obj.value;
            }
        },
        fmtNum(n_str, dp = 2) {
            try {
                let f = parseFloat(n_str);
                return f.toFixed(dp);
            } catch (err) {
                console.error("fmtNum: failed to parse as float. " + err);
                return n_str;
            }
        },
        get_course_label(s) {
            return s.course.code + ' ' + s.course.title +
                ' Sec. ' + s.course.section +
                ' (' + s.acad_session + ') : ' +
                this.labelFor(this.SD.Departments, s.course.dept_name);
        },
        isCourseRegOpen(acad_session) {
            return this.$root.eventsStatusMap.includes(`${acad_session}:COURSE_REG`);
        },
        isGradeSubOpen(acad_session) {
            return this.$root.eventsStatusMap.includes(`${acad_session}:GRADE_SUB`);
        },
        isCourseWithdrawOpen(acad_session) {
            return this.$root.eventsStatusMap.includes(`${acad_session}:WITHDRAW`);
        },
        isCourseAddDropOpen(acad_session) {
            return this.$root.eventsStatusMap.includes(`${acad_session}:ADD_DROP`) ||
                this.$root.eventsStatusMap.includes(`${acad_session}:COURSE_REG`);
        },
        isLowAttendance(pct) {
            // pct is domain.attendance.percent_for_enrolment()'s mixed
            // return: the int 0 (no attendance recorded yet) or a
            // two-decimal string. Number() handles both. Purely a display
            // hint -- nothing is blocked by falling below the threshold.
            const min = this.SD && this.SD.MinAttendancePercentRequired;
            return min != null && pct !== "" && pct != null && Number(pct) < min;
        },
    },
    computed: {
        eventsStatus: {
            get: function () {
                return this.$root.eventsStatusMap;
            },
            // setter
            set: function (newValue) {
                return this.$root.eventsStatusMap = newValue;
            }
        },
        viewOnly: {
            get: function () {
                return this.$root.viewOnlyFlag;
            },
            // setter
            set: function (newValue) {
                return this.$root.viewOnlyFlag = newValue;
            }
        },
        SD() {
            return this.$root.staticData;
        },
        currentUser() {
            return this.$root.user;
        },
        isOAuth: {
            get: function () {
                return this.$root.is_oauth;
            },
            set: function (val) {
                return this.$root.is_oauth = val;
            }
        },
        statusMsg() {
            return this.$root.statusMessage;
        },
        authenticated() {
            return this.$root.user.login_id !== undefined
        },
        userRole() {
            return this.$root.user.role
        },
        loginId() {
            return this.$root.user.login_id
        },
        thisUser() {
            return this.$root.user
        },
        isStudent() {
            return this.$root.user.role === 'STU'
        },
        isSuperuser() {
            return this.$root.user.role === 'SUP'
        },
        isFaculty() {
            return this.$root.user.role === 'FAC'
        },
        isAcad() {
            return this.$root.user.role === 'ACA'
        },
        isDean() {
            return this.$root.user.role === 'DEA'
        },
        isHod() {
            return this.$root.user.role === 'HOD'
        },
        isPlacement() {
            return this.$root.user.role === 'PLA'
        },
        isPhdStudent() {
            return this.$root.user.role === 'STU' && this.$root.user.degree === 'PHD'
        },
        isUGStudent() {
            return this.$root.user.role === 'STU' && this.$root.user.degree === 'BTE'
        },
        isPGStudent() {
            return this.$root.user.role === 'STU' &&
                !["PHD", "BTE"].includes(this.$root.user.degree)
        },
        acadSessionRegExp() {
            return new RegExp("^\\d{4}-([S]|I{0,2}|T[1-4])$", "i");
        }
    }
})

app.mount('#app')
