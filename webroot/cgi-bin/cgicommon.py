#!/usr/bin/python

import sys;
import os;
import cgi;
import urllib;

dbdir = os.path.join("..", "tourneys");

def print_html_head(title):
	print """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-GB" xml:lang="en-GB">
""";
	print "<head>";
	print "<title>%s</title>" % (cgi.escape(title));
	print "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />";
	print "<link rel=\"stylesheet\" type=\"text/css\" href=\"/style.css\" />";
	print "</head>";

def show_tourney_exception(exc):
	print "<blockquote>";
	print "<strong>%s</strong>" % cgi.escape(exc.description);
	print "</blockquote>";

def set_module_path():
	generator_dir = os.environ.get("GENERATORPATH", ".");
	code_dir = os.environ.get("CODEPATH", os.path.join("..", "..", "py"));
	sys.path.append(generator_dir);
	sys.path.append(code_dir);


def show_sidebar(tourney):
	print "<div class=\"sidebar\">";

	print "<a href=\"/cgi-bin/home.py\">Home</a><br />";
	if tourney:
		print "<p><strong>%s</strong></p>" % cgi.escape(tourney.name);
		print "<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">Setup</a><br />" % urllib.quote_plus(tourney.name);
		print "<br />";

		print "<a href=\"/cgi-bin/teleost.py?tourney=%s\">Display Control</a><br />" % urllib.quote_plus(tourney.name);
		print "<br />";

		rounds = tourney.get_rounds();
		for r in rounds:
			round_no = r["num"];
			round_type = r["type"];
			round_name = r.get("name", None);
			if not round_name:
				round_name = "Round " + str(round_no);

			print "<div class=\"roundlink\">";
			print "<a href=\"/cgi-bin/games.py?tourney=%s&round=%s\">%s</a>" % (urllib.quote_plus(tourney.name), urllib.quote_plus(str(round_no)), cgi.escape(round_name));
			print "</div>";
		print "<br />";
		print "<div class=\"genroundlink\">";
		print "<a href=\"/cgi-bin/fixturegen.py?tourney=%s\">Generate new round...</a>" % (urllib.quote_plus(tourney.name));
		print "</div>";

		print "<div class=\"standingslink\">";
		print "<a href=\"/cgi-bin/standings.py?tourney=%s\">Standings</a>" % (urllib.quote_plus(tourney.name));
		print "</div>";
	print "</div>";
