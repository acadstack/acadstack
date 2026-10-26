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
            let res;
            try {
                res = isGet ? await vm.$http.get(url) : await vm.$http.post(url, postData);
            } catch (error) {
                console.log(error);
                vm.setStatusMessage(vm.httpErrorMessage(error), 'error');
                return;
            }
            try {
                if (res.data.status == "OK") {
                    onOk(res.data.body)
                } else {
                    onError(res.data.body)
                    // Messages set by the error callback are shown as errors
                    if (vm.$root.statusMessage && vm.$root.statusKind == 'info') {
                        vm.$root.statusKind = 'error';
                    }
                }
            } catch (error) {
                console.error(error);
                vm.setStatusMessage("The page could not show the result of your request. " +
                    "Please reload the page and check whether your change was saved.", 'error');
            }
        },
        httpErrorMessage(error) {
            const resp = error && error.response;
            if (!resp) {
                return "Could not reach the server. Please check your network connection and try again.";
            }
            if (resp.status == 401 || resp.status == 403) {
                return "Your session has expired or you are not allowed to do this. Please log in again.";
            }
            if (resp.status >= 500) {
                return "The server hit an unexpected error. Please try again; if it keeps failing, contact the administrator.";
            }
            if (resp.data && typeof resp.data.body === 'string') return resp.data.body;
            return "The request failed (HTTP " + resp.status + "). Please try again.";
        },
        setStaticData(sd) {
            this.$root.staticData = sd;
        },
        /**
         * Shows a message in the alert box. kind is 'info' (the default),
         * 'success' (dismissed automatically) or 'error'. A list of messages is
         * shown one per line.
         */
        setStatusMessage(msg, kind = 'info') {
            const text = Array.isArray(msg) ? msg.join("\n") : (msg ?? "");
            this.$root.statusMessage = text;
            this.$root.statusKind = kind;
            if (kind == 'success' && text) {
                setTimeout(() => {
                    if (this.$root.statusMessage === text) this.$root.statusMessage = "";
                }, 8000);
            }
        },
        setSuccessMessage(msg) {
            this.setStatusMessage(msg, 'success');
        },
        setCurrentUser(user) {
            this.$root.user = user;
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
        /**
         * Whether the user holds the permission: a plain name such as
         * "offerings.edit" at any scope, a scoped name such as
         * "fees.view:own" exactly. The same rule gates the menus (nav.json).
         */
        hasPermission(perm) {
            const perms = this.$root.user.perms || [];
            if (perm.includes(':')) return perms.includes(perm);
            return perms.some(p => p === perm || p.startsWith(perm + ':'));
        },
        isCourseAddDropOpen(acad_session) {
            return this.$root.eventsStatusMap.includes(`${acad_session}:ADD_DROP`) ||
                this.$root.eventsStatusMap.includes(`${acad_session}:COURSE_REG`);
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
        loginId() {
            return this.$root.user.login_id
        },
        thisUser() {
            return this.$root.user
        },
        /** A student acting on their own records. */
        isStudent() {
            return this.hasPermission('students.academics:own')
        },
        /**
         * The user's step in course approval: the author submits a course to
         * the HoD, the HoD forwards it to the Dean, who approves it.
         */
        courseStage() {
            if (this.hasPermission('courses.edit:any'))
                return this.hasPermission('courses.edit_approved') ? 'dean' : 'hod';
            if (this.hasPermission('courses.edit:own')) return 'author';
            return undefined;
        },
        isPhdStudent() {
            return this.isStudent && this.$root.user.degree_level === 'PHD'
        },
        isUGStudent() {
            return this.isStudent && this.$root.user.degree_level === 'UG'
        },
        isPGStudent() {
            return this.isStudent && this.$root.user.degree_level === 'PG'
        }
    }
})

app.mount('#app')
