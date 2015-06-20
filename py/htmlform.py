#!/usr/bin/python

import sys;
import cgi;

class HTMLForm(object):
	def __init__(self, method, action, element_list):
		self.element_list = element_list;
		self.method = method;
		self.action = action;
	
	def get_value(self, name):
		for el in self.element_list:
			if el.name == name:
				return el.get_value();
		return None;
	
	def set_values(self, settings):
		for key in settings:
			for el in self.element_list:
				if el.name == key:
					el.set_value(settings[key]);
	
	def get_values(self):
		settings = dict();
		for el in self.element_list:
			if el.name:
				settings[el.name] = el.get_value();
		return settings;
	
	def add_element(self, element):
		self.element_list.append(element);
	
	def html(self):
		s = "<form method=\"%s\" action=\"%s\">\n" % (cgi.escape(self.method, True), cgi.escape(self.action, True));
		for el in self.element_list:
			s += el.html();
		s += "\n</form>";
		return s;


class HTMLFormElement(object):
	def __init__(self, name):
		self.name = name;

class HTMLFragment(HTMLFormElement):
	def __init__(self, html):
		self.html_text = html;
		self.name = None;
	
	def html(self):
		return self.html_text;

	def get_value(self):
		return None;

	def set_value(self, value):
		pass;

class HTMLLineBreak(HTMLFragment):
	def __init__(self):
		super(HTMLLineBreak, self).__init__("<br />\n");

class HTMLFormChoice(object):
	def __init__(self, value, label, selected=False):
		self.value = value;
		self.label = label;
		self.selected = selected;

class HTMLFormCheckBox(HTMLFormElement):
	def __init__(self, name, label, checked):
		super(HTMLFormCheckBox, self).__init__(name);
		self.label = label;
		self.checked = checked;
	
	def get_value(self):
		return self.checked;
	
	def set_value(self, checked):
		self.checked = checked;
	
	def html(self):
		s = "<input type=\"checkbox\" name=\"%s\" value=\"1\"" % cgi.escape(self.name, True);
		if self.checked:
			s += " checked";
		s += " /> ";
		s += cgi.escape(self.label);
		return s;

class HTMLFormHiddenInput(HTMLFormElement):
	def __init__(self, name, value):
		super(HTMLFormHiddenInput, self).__init__(name);
		self.value = value;
	
	def get_value(self):
		return self.value;
	
	def html(self):
		return "<input type=\"hidden\" name=\"%s\" value=\"%s\">\n" % (cgi.escape(self.name, True), cgi.escape(self.value, True));

class HTMLFormTextInput(HTMLFormElement):
	def __init__(self, label, name, value, length=None, other_attrs=None):
		super(HTMLFormTextInput, self).__init__(name);
		self.label = label;
		self.value = value;
		self.length = length;
		self.other_attrs = other_attrs;
	
	def get_value(self):
		return self.value;

	def html(self):
		s = "%s <input type=\"text\" name=\"%s\" value=\"%s\"" % (self.label, cgi.escape(self.name, True), cgi.escape(self.value, True));
		if self.length:
			s += " length=\"%d\"" % int(self.length);
		if self.other_attrs:
			for name in self.other_attrs:
				s += " %s=\"%s\"" % (cgi.escape(name), cgi.escape(self.other_attrs[name], True));
			
		s += " />";
		return s;


class HTMLFormRadioButton(HTMLFormElement):
	def __init__(self, name, label, choices):
		super(HTMLFormRadioButton, self).__init__(name);
		self.label = label;
		self.choices = choices;
	
	def get_value(self):
		for c in self.choices:
			if c.selected:
				return c.value;
		return None;

	def set_value(self, value):
		for c in self.choices:
			if c.value == value:
				c.selected = True;
			else:
				c.selected = False;

	def html(self):
		s = self.label;
		s += "<br />";
		for c in self.choices:
			if c.selected:
				checked = "checked";
			else:
				checked = "";
			s += "<input type=\"radio\" name=\"%s\" value=\"%s\" %s /> %s" % (cgi.escape(self.name, True), cgi.escape(c.value, True), checked, cgi.escape(c.label));
			s += "<br />\n";
		return s;

class HTMLFormSubmitButton(HTMLFormElement):
	def __init__(self, name, value, other_attrs=None):
		super(HTMLFormSubmitButton, self).__init__(name);
		self.value = value;
		self.other_attrs = other_attrs;
	
	def get_value(self):
		return self.value;
	
	def set_value(self, value):
		self.value = value;
	
	def html(self):
		s = "<input type=\"submit\" name=\"%s\" value=\"%s\" " % (cgi.escape(self.name, True), cgi.escape(self.value, True));
		if self.other_attrs:
			for name in self.other_attrs:
				s += "%s=\"%s\" " % (cgi.escape(name), cgi.escape(self.other_attrs[name], True));
		s += "/>\n";
		return s;

class HTMLFormDropDownOption(HTMLFormElement):
	def __init__(self, value, label=None, selected=False):
		super(HTMLFormDropDownOption, self).__init__(None);
		self.value = value;
		if label is None:
			label = value;
		self.label = label;
		self.selected = selected;
	
	def get_value(self):
		return self.value;
	
	def is_selected(self):
		return self.selected;
	
	def set_selected(self, selected):
		self.selected = bool(selected);
	
	def html(self):
		s = "<option value=\"%s\"" % cgi.escape(self.value, True);
		if self.selected:
			s += " selected";
		s += ">%s</option>\n" % (cgi.escape(self.label));
		return s;

class HTMLFormDropDownBox(HTMLFormElement):
	def __init__(self, name, options):
		super(HTMLFormDropDownBox, self).__init__(name);
		self.options = options[:];
	
	def get_value(self):
		for o in self.options:
			if o.is_selected():
				return o.get_value();
		return None;
	
	def set_value(self, value):
		for o in self.options:
			if o.get_value() == value:
				o.set_selected(True);
			else:
				o.set_selected(False);
	
	def html(self):
		s = "<select name=\"%s\">\n" % (cgi.escape(self.name, True));
		for o in self.options:
			s += o.html();
		s += "</select>\n";
		return s;

