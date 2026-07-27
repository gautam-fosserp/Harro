frappe.ui.form.on("Task", {
    refresh:function(frm){
        set_new_task_defaults(frm);
        if(frm.doc.working_status != "Work In Progress" && frm.doc.status != "Completed" && frm.doc.working_status != "On Hold"){
            frm.add_custom_button(__("Start Timer"), function(){
                update_start_job_log(frm)
                frm.trigger("make_dashboard");
            }).addClass("btn-primary");
        }
        if(frm.doc.working_status == "Work In Progress"){
            frm.add_custom_button(__("Pause Timer"), function(){
                update_stop_job_log(frm)
                frm.trigger("make_dashboard");
            }).addClass("btn-primary");
        }
        if(frm.doc.working_status == "On Hold"){
            frm.add_custom_button(__("Resume Timer"), function(){
                update_start_job_log(frm)
                frm.trigger("make_dashboard");
            }).addClass("btn-primary");
        }
        frm.trigger("make_dashboard");
        // 
        frm.set_query("completed_by", {
			filters: {
				"name": frappe.session.user,
			},
		});

		frm.dashboard.refresh();
		frm.trigger('show_task_dependency_progress');
    },
    make_dashboard: function (frm) {
		if (frm.doc.__islocal) return;

		function setCurrentIncrement() {
			currentIncrement += 1;
			return currentIncrement;
		}

		function updateStopwatch(increment) {
			var hours = Math.floor(increment / 3600);
			var minutes = Math.floor((increment - hours * 3600) / 60);
			var seconds = increment - hours * 3600 - minutes * 60;

			$(section)
				.find(".hours")
				.text(hours < 10 ? "0" + hours.toString() : hours.toString());
			$(section)
				.find(".minutes")
				.text(minutes < 10 ? "0" + minutes.toString() : minutes.toString());
			$(section)
				.find(".seconds")
				.text(seconds < 10 ? "0" + seconds.toString() : seconds.toString());
		}

		function initialiseTimer() {
			const interval = setInterval(function () {
				var current = setCurrentIncrement();
				updateStopwatch(current);
			}, 1000);
		}

		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold;margin:0px 13px 0px 2px;
				color:#545454;font-size:18px;display:inline-block;vertical-align:text-bottom;>
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.toolbar.page.add_inner_message(timer);

		let currentIncrement =  0;
        let started_time = null;

        if (frm.doc.unproductive_work_timelogs && frm.doc.unproductive_work_timelogs.length) {
            started_time = frm.doc.unproductive_work_timelogs[frm.doc.unproductive_work_timelogs.length - 1].from_time;
        }
        
		if (started_time) {
			if (frm.doc.working_status == "On Hold") {
				updateStopwatch(currentIncrement);
			} else {
                console.log(frappe.datetime.now_datetime())
                console.log(started_time)
				currentIncrement += moment(frappe.datetime.now_datetime()).diff(
					moment(started_time),
					"seconds"
				);
				initialiseTimer();
			}
		}
	},
    custom_assigned_to_responsible_user:(frm)=>{
        if (frm.doc.custom_assigned_to_responsible_user){
            frappe.call({
                method : "harro.harro.docevents.task.get_employee_id",
                args: {
                    user : frm.doc.custom_assigned_to_responsible_user
                },
                callback:(r)=>{
                    if(r.message){
                        frm.set_value("custom_employee__assign_to_employee_", r.message)
                    }
                }
            })
        }
    },
    // 
    show_task_dependency_progress(frm) {
        if (frm.doc.__islocal) return;
        
		let rows = frm.doc.depends_on || [];
		let completed = 0;
		let total = 0;
		let promises = [];

		if (!rows.length) {
			return;
		}

		rows.forEach(row => {
			if (row.task) {
				total++;
				promises.push(
					frappe.db.get_value('Task', row.task, 'status')
						.then(r => {
							if (r.message?.status === 'Completed') {
								completed++;
							}
						})
				);
			}
		});

		if (!total) {
			add_task_progress(frm, 0, 0);
			return;
		}

		Promise.all(promises).then(() => {
			add_task_progress(frm, completed, total);
		});
	},
    status(frm) {
        if(frm.doc.status == "Completed"){
            frm.set_value("completed_by", frappe.session.user)
        }
    },
    custom_employee__assign_to_employee_(frm) {
        if (!frm.doc.custom_employee__assign_to_employee_) return;
        frappe.model.get_value("Employee", frm.doc.custom_employee__assign_to_employee_, "department", (r)=>{
            frm.set_value("department", r.department)
        })
    } 
})

// 
function set_new_task_defaults(frm) {
    let task_docfield = frm.get_docfield("depends_on", "task");
    if (!task_docfield) return;

    task_docfield.get_route_options_for_new_doc = function(control) {
        return {
            "parent_task": frm.doc.name,
            "project": frm.doc.project
        };
    };
}

// 
function add_task_progress(frm, completed, total) {

	let percent = total ? Math.round((completed / total) * 100) : 0;
	let width = percent === 0 ? '0.5%' : percent + '%';

	let title = __('{0} of {1} tasks completed ({2}%)', [
		completed,
		total,
		percent
	]);

	let bars = [{
		title: title,
		width: width,
		progress_class: 'progress-bar-success'
	}];

	frm.dashboard.add_progress(__('Dependency Status'), bars, title);
}

// 
function update_start_job_log(frm){
    let d = new frappe.ui.Dialog({
        title: 'Update Time log',
        fields: [
            {
                "fieldname" : "activity_type",
                "label" : "Activity Type",
                "options" : "Activity Type",
                "reqd" :  1,
                "fieldtype" : "Link",
                get_query: function () {
                    return {
                        query : "harro.harro.docevents.task.get_activity_type",
                        filters: {
                            custom_unproductive_work : 0,
                            department : frm.doc.department
                        },
                    };
                },
            },
            {
                "fieldname" : "project",
                "label" : "BA Number",
                "options" : "Project",
                "reqd" :  1,
                "fieldtype" : "Link",
                "default" : frm.doc.project
            },
            {
                "fieldname" : "task",
                "label" : "Task",
                "options" : "Task",
                "reqd" :  0,
                "fieldtype" : "Link",
                "read_only" : 1
            },
            {
                "fieldname" : "employee",
                "label" : "Employee",
                "options" : "Employee",
                "reqd" :  1,
                "fieldtype" : "Link",
                "read_only" : 0
            },
        ],
        size: 'small', // small, large, extra-large 
        primary_action_label: 'Update Timesheet Log',
        primary_action(values) {
            let data = d.get_values();
            let arg = {
                activity_type : data.activity_type,
                from_time : frappe.datetime.now_datetime(),
                project : data.project,
                task : data.task,
                employee : data.employee
            }
            frappe.call({
                method: "harro.harro.docevents.task.update_time_log",
                args : {
                    arg : arg,
                },
                callback:(r)=>{
                    frm.refresh_field("custom_unproductive_work_timelogs")
                    frm.reload_doc()
                    d.hide();
                }
            })
        }
    });
    d.show()
    d.set_value("project", frm.doc.project)
    d.set_value("task", frm.doc.name)
    d.set_value("employee", frm.doc.custom_employee__assign_to_employee_)
}

function update_stop_job_log(frm){
    let arg = {
        task : frm.doc.name,
        to_time : frappe.datetime.now_datetime()
    }
    frappe.call({
        method : "harro.harro.docevents.task.update_stop_task_log",
        args : {
            arg: arg,
        },
        callback:(r)=>{
            frm.reload_doc()
        }
    })
}