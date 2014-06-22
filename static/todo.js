$(function () {

	$.app = {};

	$.app.emptySlotText = 'Do nothing!';

	// Models

	$.app.Task = Backbone.RelationalModel.extend({

		urlRoot: '/tasks',

		toggle: function() {
			this.save({done: !this.get("done")});
		},

		defaults: {
			"done": false,
			"description": $.app.emptySlotText
		}

	});

	$.app.List = Backbone.RelationalModel.extend({

		urlRoot: '/lists',

		initialize: function() {
			this.listenTo(this.get('tasks'), 'collection-changed', this.on_collection_changed);
		},
		
		relations: [{
			type: Backbone.HasMany,
			collectionType: '$.app.Tasks',
			key: 'tasks',
			relatedModel: '$.app.Task',
			includeInJSON: 'id',
			autoFetch: true,
		}],

		defaults: {
			"description": "Todos",
			"tasks": []
		},

		on_collection_changed: function () {
			this.save();  // Saving the Tasks model
		}

	});

	// Collections

	$.app.Tasks = Backbone.Collection.extend({

		model: $.app.Task,

		initialize: function() {
			this.listenTo(this, 'change add remove', this.render_remaining);
			this.listenTo(this, 'remove-task', this.remove_task);
		},

		remaining: function() {
			return this.where({done: false});
		},

		render_remaining: function() {
			var remaining = this.remaining().length;
      var message;
			if (remaining === 0) {
				message = 'All tasks completed! :)';
			} else if (remaining == 1) {
				message = 'Only 1 task left!';
			} else {
				message = remaining + ' tasks remaining...';
			}
			$('#todo-count').html(message);
		},

		complete_all: function () {
			_.each(
        this.model.get('tasks').remaining(),
        function (tsk) { tsk.toggle(); });
		},

		remove_task: function(model) {
			model.collection.remove(model);
			this.trigger('collection-changed');
		}

	});

	// Views

	$.app.ListView = Backbone.View.extend({

		initialize: function() {
			_.bindAll(this, 'render', 'render_task', 'submit');
			this.model.bind('change', this.render);
			this.model.bind('reset', this.render);
			this.model.bind('add:tasks', this.render_task);
			this.model.bind('remove:tasks', this.remove_task_view);
		},

		template: Handlebars.compile($('#list-template').html()),

		render: function() {
			var self = this;
			var rendered = $(this.el).html(this.template(this.model.toJSON()));
			$("tbody").sortable({
				handle: ".glyphicon-resize-vertical",
				cursor: "move",
				stop: function () {
					var new_order = $('tbody').sortable('toArray');
					new_order = _.map(
						new_order,
						function (x) { return parseInt(x); }
					);
					self.model.save({tasks: new_order});
				}
			});
			this.$('#complete-all').on('click', function () {
				self.trigger('complete-all');
			});
			this.listenTo(this, 'complete-all', $.app.Tasks.prototype.complete_all);
			return rendered;
		},

		render_task: function(task) {
			var task_view = new $.app.TaskView({model: task});
			this.$('tbody').append($(task_view.render()));
		},

		remove_task_view: function() {
			this.save();  // Removing task from Tasks model
		},

		events: {
			'submit #add-task': 'submit',
		},

		submit: function(e) {
			e.preventDefault();
			var new_task = new $.app.Task({
				description: this.$('#new-task-description').val() || $.app.emptySlotText,
				done: false});
			var listModel = this.model;
			listModel.get('tasks').add(new_task, {});
			new_task.save(null, {
				success: function() {
					listModel.save();
					this.$('#new-task-description').val("");
				},
			});
		},

	});

	$.app.TaskView = Backbone.View.extend({

		tagName: 'tr',

		className: 'task-view',

		initialize: function(){
			//_.bindAll(this, 'render');
			// this.model.bind('change', this.render);
			this.listenTo(this.model, 'change', this.render);
		},

		template: Handlebars.compile($('#task-template').html()),

		render: function() {
			this.$el.html(this.template(this.model.toJSON()));
			this.$el.toggleClass('done', this.model.get('done'));
			this.$('.edit').hide();
			this.$el.attr('id', this.model.id);  // Needed for jQuery sortable
			return this.$el;
		},

		events: {
			"click .toggle"   : "toggleDone",
			"dblclick .view"  : "edit",
			"click .remove"   : "remove_task",
			"keypress .edit"  : "updateOnEnter",
			"blur .edit"      : "update"
		},

		toggleDone: function() {
			this.model.toggle();
		},

		edit: function() {
			this.$('.view').hide();
			this.$('.edit').addClass("editing").show();
			var endOfInputHack= this.$('.edit').val();
			this.$('.edit').focus().val('').val(endOfInputHack);
		},

		update: function() {
			var value = this.$('.edit').val() || $.app.emptySlotText;
			this.model.save({description: value});
			this.$('.edit').hide();
			this.$('.view').show();
		},

		updateOnEnter: function(ev) {
			if (ev.keyCode == 13) this.update();
		},

		remove_task: function() {
			this.$el.remove();
			this.model.trigger('remove-task', this.model);
		}

	});

	// Routing

	$.app.Router = Backbone.Router.extend({

		routes: {
			"": "home",
			"lists/:id": "todolist"
		},

		home: function () {
			var self = this;
			var list = new $.app.List();
			list.save(null, {
				success: function(model) {
					self.navigate("lists/" + model.id);
					var list_view = new $.app.ListView({el: $('#app-container'), model: list});
					list_view.render();
				}
			});
		},

		todolist: function (id) {
			var list = new $.app.List({id: id});
			list.fetch();
			var list_view = new $.app.ListView({el: $('#app-container'), model: list});
			list_view.render();
		}

	});

	// Execution

	$.app.router = new $.app.Router();
	Backbone.history.start();

});