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
                    Events dates for academic session (I = First Semester, II = Second Semester, S=Summer):
                    <input :disabled="viewOnly" v-model.trim="acad_dates.session" maxlength="7" placeholder="YYYY-S" />
                    <div v-if="!v$.acad_dates.session.validsession && v$.acad_dates.session.$dirty"
                        class="text-danger">Session is invalid</div>
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
            </div>
            <div class="card-body">
                <div class="row hdr-row mb-2 border-info border-bottom">
                    <div class="col">Event</div>
                    <div class="col-md-3">Start Date</div>
                    <div class="col-md-3">End Date</div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Academic session</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.SESSION_S"
                            :rule="v$.acad_dates.eventDates.SESSION_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.SESSION_E"
                            :rule="v$.acad_dates.eventDates.SESSION_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Course pre-registration</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.COURSE_REG_S"
                            :rule="v$.acad_dates.eventDates.COURSE_REG_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.COURSE_REG_E"
                            :rule="v$.acad_dates.eventDates.COURSE_REG_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Classes</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.CLASSES_S"
                            :rule="v$.acad_dates.eventDates.CLASSES_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.CLASSES_E"
                            :rule="v$.acad_dates.eventDates.CLASSES_E" />
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Course drop</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.ADD_DROP_S"
                            :rule="v$.acad_dates.eventDates.ADD_DROP_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.ADD_DROP_E"
                            :rule="v$.acad_dates.eventDates.ADD_DROP_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Midsem course feedback</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.FEEDBACK_MID_S"
                            :rule="v$.acad_dates.eventDates.FEEDBACK_MID_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.FEEDBACK_MID_E"
                            :rule="v$.acad_dates.eventDates.FEEDBACK_MID_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Mid sem exams</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.MINOR_EXAM_S"
                            :rule="v$.acad_dates.eventDates.MINOR_EXAM_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.MINOR_EXAM_E"
                            :rule="v$.acad_dates.eventDates.MINOR_EXAM_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Withdraw</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.WITHDRAW_S"
                            :rule="v$.acad_dates.eventDates.WITHDRAW_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.WITHDRAW_E" 
                            :rule="v$.acad_dates.eventDates.WITHDRAW_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">End sem exams</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.MAJOR_EXAM_S"
                            :rule="v$.acad_dates.eventDates.MAJOR_EXAM_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.MAJOR_EXAM_E" 
                            :rule="v$.acad_dates.eventDates.MAJOR_EXAM_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Course feedback</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.FEEDBACK_S" 
                            :rule="v$.acad_dates.eventDates.FEEDBACK_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.FEEDBACK_E" 
                            :rule="v$.acad_dates.eventDates.FEEDBACK_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Grades submission</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.GRADE_SUB_S" 
                            :rule="v$.acad_dates.eventDates.GRADE_SUB_S"/>
                    </div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.GRADE_SUB_E" 
                            :rule="v$.acad_dates.eventDates.GRADE_SUB_E"/>
                    </div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Show feedback (midsem)</div>
                    <div class="col-md-3">
                        <date-input v-model.trim="acad_dates.eventDates.SHOW_MIDSEM_FB_S" 
                            :rule="v$.acad_dates.eventDates.SHOW_MIDSEM_FB_S"/>
                    </div>
                    <div class="col-md-3">N/A</div>
                </div>
                <div class="row row-striped mb-2">
                    <div class="col">Show feedback (endsem)</div>
                    <div class="col-md-3">
                        <date-input v-model="acad_dates.eventDates.SHOW_ENDSEM_FB_S" 
                            :rule="v$.acad_dates.eventDates.SHOW_ENDSEM_FB_S"/>
                    </div>
                    <div class="col-md-3">N/A</div>
                </div>
                <div class="row row-striped ">
                    <div class="col">Result Declaration</div>
                    <div class="col-md-3">
                        <date-input v-model="acad_dates.eventDates.RESULT_DECLARATION" 
                            :rule="v$.acad_dates.eventDates.RESULT_DECLARATION"/>
                    </div>
                    <div class="col-md-3">N/A</div>
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
                eventDates: {
                    SESSION_S: "", SESSION_E: "",
                    COURSE_REG_S: "", COURSE_REG_E: "",
                    CLASSES_S: "", CLASSES_E: "",
                    MINOR_EXAM_S: "", MINOR_EXAM_E: "",
                    FEEDBACK_MID_S: "", FEEDBACK_MID_E: "",
                    FEEDBACK_S: "", FEEDBACK_E: "",
                    MAJOR_EXAM_S: "", MAJOR_EXAM_E: "",
                    GRADE_SUB_S: "", GRADE_SUB_E: "",
                    WITHDRAW_S: "", WITHDRAW_E: "",
                    SHOW_MIDSEM_FB_S: "", SHOW_ENDSEM_FB_S: "",
                    RESULT_DECLARATION: "", ADD_DROP_S: "",
                    ADD_DROP_E: ""
                }
            }
        }
    },
    created: function () {
        let vm = this;
        vm.viewOnly = !vm.hasPermission("academic_calendar.manage_dates");
    },
    methods: {
        onAcadSessionChange(acs) {
            this.session = acs;
            this.search();
        },
        are_dates_within_session() {
            let vm = this;
            let valid = true;
            const m = vm.acad_dates.eventDates;
            for (const dt in m) {
                if (dt.startsWith("SESSION_")) continue;
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
                    .post("dates_save", vm.acad_dates)
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
                eventDates: {
                    SESSION_S: "", SESSION_E: "",
                    COURSE_REG_S: "", COURSE_REG_E: "",
                    CLASSES_S: "", CLASSES_E: "",
                    MINOR_EXAM_S: "", MINOR_EXAM_E: "",
                    FEEDBACK_MID_S: "", FEEDBACK_MID_E: "",
                    FEEDBACK_S: "", FEEDBACK_E: "",
                    MAJOR_EXAM_S: "", MAJOR_EXAM_E: "",
                    GRADE_SUB_S: "", GRADE_SUB_E: "",
                    WITHDRAW_S: "", WITHDRAW_E: "",
                    SHOW_MIDSEM_FB_S: "", SHOW_ENDSEM_FB_S: "",
                    RESULT_DECLARATION: ""
                }
            }
        }
    },
    validations() {
        return {
            session: {
                required,
                validsession() {
                    return this.acadSessionRegExp.test(this.session);
                }
            },
            acad_dates: {
                session: {
                    required,
                    validsession() {
                        return this.acadSessionRegExp.test(this.acad_dates.session);
                    }
                },
                eventDates: {
                    SESSION_S: {
                        required
                    },
                    SESSION_E: {
                        required
                    },
                    COURSE_REG_S: {
                        required
                    },
                    COURSE_REG_E: {
                        required
                    },
                    CLASSES_S: {
                        required
                    },
                    CLASSES_E: {
                        required
                    },
                    MINOR_EXAM_S: {
                        required
                    },
                    MINOR_EXAM_E: {
                        required
                    },
                    FEEDBACK_MID_S: {
                        required
                    },
                    FEEDBACK_MID_E: {
                        required
                    },
                    FEEDBACK_S: {
                        required
                    },
                    FEEDBACK_E: {
                        required
                    },
                    MAJOR_EXAM_S: {
                        required
                    },
                    MAJOR_EXAM_E: {
                        required
                    },
                    GRADE_SUB_S: {
                        required
                    },
                    GRADE_SUB_E: {
                        required
                    },
                    WITHDRAW_S: {
                        required
                    },
                    WITHDRAW_E: {
                        required
                    },
                    SHOW_MIDSEM_FB_S: {
                        required
                    },
                    SHOW_ENDSEM_FB_S: {
                        required
                    },
                    RESULT_DECLARATION: {
                        required
                    },
                    ADD_DROP_S: {
                        required
                    },
                    ADD_DROP_E: {
                        required
                    }
                }
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
