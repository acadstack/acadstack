<!--
Component for adding the academic event dates.

@author Balwinder Sodhi
-->
<template>
    <div class="container-fluid">

        <div class="row mb-2">
            <div class="col float-start">
                <acad-session v-bind:acad_session="session" label="Load for session"
                    v-on:update:acad_session='onAcadSessionChange' />
                <div v-if="!v$.session.required && v$.session.$dirty" class="text-danger">This is a requird feild</div>
                <div v-else-if="!v$.session.validsession && v$.session.$dirty" class="text-danger">Session is invalid
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">
                <span class="float-start">
                    Event dates for academic session:
                    <input :disabled="viewOnly" v-model.trim="acad_dates.session" maxlength="10" placeholder="Session name" />
                    <label class="ms-2">
                        <input type="checkbox" :disabled="viewOnly" v-model="acad_dates.is_additional" />
                        Additional session (overlaps the regular terms, e.g. summer)
                    </label>
                    <div v-if="!v$.acad_dates.session.required && v$.acad_dates.session.$dirty"
                        class="text-danger">Session name is required</div>
                </span>
                <div v-if="!viewOnly" class="float-end">
                    <button class="btn btn-outline-success me-2" type="button" @click="save">
                        Save
                        <i class="bi bi-save"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="reset" type="button">
                        Clear
                        <i class="bi bi-eraser"></i>
                    </button>
                </div>
                <div class="float-end me-2">
                    <span v-if="acad_dates.eventDates.SESSION_CLOSED" class="badge bg-secondary">
                        Closed on {{ acad_dates.eventDates.SESSION_CLOSED }}
                    </span>
                    <button v-else-if="hasPermission('sessions.close') && acad_dates.session"
                        class="btn btn-outline-warning" type="button" @click="closeSession">
                        Close session
                        <i class="bi bi-lock"></i>
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="row hdr-row mb-2 border-info border-bottom">
                    <div class="col">Event</div>
                    <div class="col-md-3">Start Date</div>
                    <div class="col-md-3">End Date</div>
                </div>
                <div class="row row-striped mb-2" v-for="r in eventRows" :key="r.code">
                    <div class="col">{{ r.label }}</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates[r.start]" :rule="rule(r.start)" />
                    </div>
                    <div class="col-md-3">
                        <date-input v-if="r.end" v-model.trim="acad_dates.eventDates[r.end]" :rule="rule(r.end)" />
                        <template v-else>N/A</template>
                    </div>
                </div>
            </div>
        </div>
    </div>

</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required } from '@vuelidate/validators'
import AcadSession from "./AcadSession.vue"
import DateInput from './DateInput.vue';

export default {
    name: "AddAcademicDates",
    components: {
        "AcadSession": AcadSession,
        "DateInput": DateInput
    },
    setup() {
        return { v$: useVuelidate() }
    },
    data: function () {
        return {
            session: "",
            acad_dates: {
                session: "",
                eventDates: {}
            }
        }
    },
    computed: {
        // One row per workflow event, then one per university-defined event.
        // SESSION_CLOSED is set only by closing the session.
        eventRows() {
            const rows = [];
            for (const e of this.SD.WorkflowEvents) {
                if (e.id == "SESSION_CLOSED") continue;
                if (e.id == "RESULT_DECLARATION")
                    rows.push({ code: e.id, label: e.value, start: e.id, required: true });
                else if (e.id.startsWith("SHOW_"))
                    rows.push({ code: e.id, label: e.value, start: e.id + "_S", required: true });
                else
                    rows.push({ code: e.id, label: e.value, start: e.id + "_S", end: e.id + "_E", required: true });
            }
            for (const e of this.SD.CalendarEvents) {
                if (e.id)
                    rows.push({ code: e.id, label: e.value, start: e.id + "_S", end: e.id + "_E", required: false });
            }
            return rows;
        },
        eventDateRules() {
            const rules = {};
            for (const r of this.eventRows) {
                if (!r.required) continue;
                rules[r.start] = { required };
                if (r.end) rules[r.end] = { required };
            }
            return rules;
        }
    },
    created: function () {
        let vm = this;
        vm.viewOnly = !vm.hasPermission('calendar.edit');
    },
    methods: {
        rule(key) {
            return this.v$.acad_dates.eventDates[key] || {};
        },
        onAcadSessionChange(acs) {
            this.session = acs;
            this.search();
        },
        are_dates_within_session() {
            let vm = this;
            let valid = true;
            const m = vm.acad_dates.eventDates;
            for (const dt in m) {
                if (dt.startsWith("SESSION_") || !m[dt]) continue;
                if (m[dt] > m["SESSION_E"] || m[dt] < m["SESSION_S"]) {
                    // console.log("m is "+m[dt]+" "+"Event is "+dt);
                    if (dt == "RESULT_DECLARATION") {
                        valid = true;
                        break;
                    }
                    else valid = false;
                    break;
                }
            }
            return valid;
        },
        async closeSession() {
            let vm = this;
            const acs = vm.acad_dates.session;
            if (!confirm(`Close session ${acs}? This freezes the credits of its enrolments, `
                + "and grade changes will need a reason. It cannot be undone.")) {
                vm.setStatusMessage("User canceled closing the session.");
                return;
            }
            await vm.doHttp(false, "close_session", {acad_session: acs}, (msg) => {
                vm.setStatusMessage(msg);
                vm.session = acs;
                vm.search();
            }, vm.setStatusMessage);
        },
        save() {
            let vm = this;
            if (vm.isViewOnly) {
                vm.setStatusMessage("You are not allowed to change academic calendar data!");
                return;
            }
            console.log('Saving academic calendar data.')
            vm.v$.acad_dates.$touch()
            if (vm.v$.acad_dates.$invalid) {
                console.error("Input validation errors!")
                return;
            }
            else {
                if (!vm.are_dates_within_session()) {
                    vm.setStatusMessage("Please ensure that all dates are within the academic session start and end dates!");
                    return;
                }

                if (!confirm("Confirm save?")) {
                    vm.setStatusMessage("User canceled save!");
                    return;
                }
                console.log("Saving Acadmic Dates");
                vm.$http
                    .post("dates_save", vm.datesToSave())
                    .then(function (res) {
                        if (res.data.status == "OK") {
                            vm.setStatusMessage("Saved successfully!");
                        } else {
                            vm.setStatusMessage(res.data.body);
                        }
                    })
                    .catch(function (error) {
                        console.log(error);
                        vm.setStatusMessage("Error occurred when contacting the server.");
                    });
            }
        },
        datesToSave() {
            const eventDates = {};
            for (const [k, v] of Object.entries(this.acad_dates.eventDates))
                if (v) eventDates[k] = v;
            return { session: this.acad_dates.session, eventDates,
                is_additional: this.acad_dates.is_additional };
        },
        search() {
            let vm = this;
            vm.v$.session.$touch()
            if (vm.v$.session.$invalid) {
                return;
            }
            else {
                console.log("Searching Acadmic Dates");
                var payload = {
                    session: vm.session
                }
                vm.$http
                    .post("dates_search", payload)
                    .then(function (res) {
                        if (res.data.status == "OK") {
                            vm.acad_dates = res.data.body
                        } else {
                            vm.setStatusMessage(res.data.body);
                        }
                    })
                    .catch(function (error) {
                        console.log(error);
                        vm.setStatusMessage("Error occurred when contacting the server.");
                    });
            }
        },
        reset() {
            this.v$.$reset();
            this.session = "";
            this.acad_dates = {
                session: "",
                eventDates: {}
            }
        }
    },
    validations() {
        return {
            session: {
                required,
                validsession() {
                    return this.isAcadSession(this.session);
                }
            },
            acad_dates: {
                session: {
                    required
                },
                eventDates: this.eventDateRules
            }
        }
    }
};
</script>
<style scoped>
.box {
    border: 1px;
    background: grey;
}
</style>
