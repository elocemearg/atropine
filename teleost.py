#!/usr/bin/python

import pygame;
import os;
import sys;
import time;
import traceback;

teleost_version = "0.2";
local_view_switching = False;

view_key_map = {
		pygame.K_1: 0,
		pygame.K_2: 1,
		pygame.K_3: 2,
		pygame.K_4: 3,
		pygame.K_5: 4,
		pygame.K_6: 5,
		pygame.K_7: 6,
		pygame.K_8: 7,
		pygame.K_9: 8,
		pygame.K_0: 9
};

os.chdir(os.path.dirname(os.path.abspath(__file__)));
sys.path.append(os.path.join(os.getcwd(), "py"));

import teleostscreen;
import teleostfetchers;
import countdowntourney;

def make_full_screen_fetcher_view(view_title, view_description, title_text, fetcher, num_lines):
	v = teleostscreen.View(name=view_title, desc=view_description);

	# Add title area and title text
	v.add_view(teleostscreen.ShadedArea(24, colour=(0, 128, 255)), top_pc=0, height_pc=13, left_pc=0, width_pc=100);
	v.add_view(teleostscreen.LabelWidget(title_text, left_pc=6, top_pc=4, height_pc=7, width_pc=100));
	v.add_view(teleostscreen.TableWidget(fetcher, num_lines), top_pc=15, height_pc=85, left_pc=5, width_pc=90);
	return v;

try:
	argpos = 1;
	if argpos < len(sys.argv) and sys.argv[argpos] == "-l":
		local_view_switching = True;
		argpos += 1;

	if argpos >= len(sys.argv):
		print "Welcome to Teleost!"
		print
		print "I can see the following tourneys:"

		tourney_list = os.listdir("tourneys");
		tourney_list = map(lambda x : x[:-3], filter(lambda x : (len(x) > 3 and x[-3:] == ".db"), tourney_list));
		tourney_list = sorted(tourney_list);

		for t in tourney_list:
			print "\t%s" % t;
		
		answer = None;
		while answer is None:
			answer = raw_input("Which tourney do you want to use? ");
			if answer not in tourney_list:
				print "Nope, can't find that one.";
				answer = None;
			else:
				break;

		tourney_name = answer;
	else:
		tourney_name = sys.argv[argpos];

	try:
		tourney = countdowntourney.tourney_open(tourney_name, "tourneys");
	except countdowntourney.TourneyException as e:
		print "Unable to open tourney...";
		print e.description;
		sys.exit(1);

	pygame.init();

	standings_fetcher = teleostfetchers.StandingsFetcher(tourney);
	videprinter_fetcher = teleostfetchers.VideprinterFetcher(tourney);
	table_results_fetcher = teleostfetchers.TableResultsFetcher(tourney);
	highest_winning_scores_fetcher = teleostfetchers.HighestWinningScoresFetcher(tourney);
	highest_losing_scores_fetcher = teleostfetchers.HighestLosingScoresFetcher(tourney);
	highest_joint_scores_fetcher = teleostfetchers.HighestJointScoresFetcher(tourney);
	overachievers_fetcher = teleostfetchers.OverachieversFetcher(tourney);
	quickest_finishers_fetcher = teleostfetchers.QuickestFinishersFetcher(tourney);
	current_round_fixtures_fetcher = teleostfetchers.CurrentRoundFixturesFetcher(tourney);
	tuff_luck_fetcher = teleostfetchers.TuffLuckFetcher(tourney);

	#fontfilename = "/usr/share/fonts/truetype/futura/Futura Condensed Bold.ttf";

	standings_widget = teleostscreen.TableWidget(standings_fetcher, 9, scroll_interval=10);

	standings_videprinter = teleostscreen.View(name="Standings / Videprinter", desc="Standings table taking up most of the screen, with latest results displayed on a scrolling window below.");

	standings_videprinter.add_view(standings_widget, top_pc=5, height_pc=65, left_pc=0, width_pc=95);
	standings_videprinter.add_view(teleostscreen.ShadedArea(128), top_pc=72, height_pc=30, left_pc=0, width_pc=100);
	standings_videprinter.add_view(teleostscreen.VideprinterWidget(videprinter_fetcher, 4), top_pc=73, height_pc=25, left_pc=2, width_pc=100);

	standings_results = teleostscreen.View(name="Standings / Table Results", desc="Standings table taking up most of the screen, with this round's fixtures and results displayed at the bottom.");
	standings_results.add_view(standings_widget, top_pc=5, height_pc=65, left_pc=0, width_pc=95);
	standings_results.add_view(teleostscreen.ShadedArea(128), top_pc=72, height_pc=30, left_pc=0, width_pc=100);
	standings_results.add_view(teleostscreen.TableWidget(table_results_fetcher, 4, scroll_interval=5), top_pc=73, height_pc=26, left_pc=0, width_pc=100);

	notables = teleostscreen.TimedViewCycler(name="Records", desc="Highest winning scores, losing scores and combined scores.");

	for (text, fetcher) in [
			("Highest winning scores", highest_winning_scores_fetcher),
			("Highest losing scores", highest_losing_scores_fetcher),
			("Highest joint scores", highest_joint_scores_fetcher)
		]:
		v = teleostscreen.View();
		v.add_view(teleostscreen.ShadedArea(24, colour=(0,128,255)), top_pc=0, height_pc=13, left_pc=0, width_pc=100);
		v.add_view(teleostscreen.LabelWidget(text, left_pc=6, top_pc=4, height_pc=7, width_pc=100));
		v.add_view(teleostscreen.TableWidget(fetcher, 12), top_pc=15, height_pc=85, left_pc=5, width_pc=90);
		notables.add_view(v, 10);
	
	overachievers = make_full_screen_fetcher_view("Overachievers", "Display table of players ranked by how high they rank above their seed.", "Overachievers", overachievers_fetcher, 12);

	quickest_finishers = make_full_screen_fetcher_view("Fastest Finishers", "An excellent way to highlight which tables are taking too long to finish their games.", "Fastest Finishing Tables", quickest_finishers_fetcher, 12);

	tuff_luck = make_full_screen_fetcher_view("Tuff Luck", "Players who have lost three or more games ordered by the sum of their three lowest losing margins.", "Tuff Luck", tuff_luck_fetcher, 12);

	fixtures = teleostscreen.View(name="Fixtures", desc="Display all fixtures in the current round, using the whole screen to do it.");
	fixtures.add_view(teleostscreen.PagedFixturesWidget(current_round_fixtures_fetcher, num_lines=13, scroll_interval=10), top_pc=0, left_pc=0, width_pc=100, height_pc=100);

	view_list = [standings_videprinter, standings_results, fixtures, overachievers, tuff_luck, notables, quickest_finishers];

	modes = [];
	modes.append((0, "Auto", "Automatic control."));
	view_num = 1;
	for v in view_list:
		name = v.get_name();
		desc = v.get_description();
		modes.append((view_num, name, desc));
		view_num += 1;

	tourney.define_teleost_modes(modes);
	tourney.set_teleost_mode(0);

	screen_width = 640;
	screen_height = 480;
	fullscreen = False;
	screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE);

	last_redraw = 0;
	redraw_interval = 2;
	if os.path.exists("background.jpg"):
		background = pygame.image.load("background.jpg");
	else:
		background = None;

	background_scaled = None;
	resized = False;

	current_view_index = 0;
	new_view_index = None;
	last_mode_check = 0;
	mode_check_interval = 2;
	title_bar = True;
	db_mode_checks = not local_view_switching;

	while True:
		if resized:
			resized = False;
			flags = pygame.RESIZABLE;
			if not title_bar:
				flags |= pygame.NOFRAME
			screen = pygame.display.set_mode((screen_width, screen_height), flags);
			last_redraw = 0;
			background_scaled = None;

		if db_mode_checks and (last_mode_check + mode_check_interval <= time.time()):
			teleost_mode = tourney.get_current_teleost_mode();
			last_mode_check = time.time();
			if teleost_mode == 0:
				knockout_phase = False;
				latest_round_no = tourney.get_latest_round_no();
				if not latest_round_no:
					if current_view_index != 0:
						new_view_index = 0;
				else:
					latest_round_type = tourney.get_round_type(latest_round_no);
					if latest_round_type != 'P':
						knockout_phase = True;
					(played, unplayed) = tourney.get_played_unplayed_counts(round_no=latest_round_no);
					if knockout_phase:
						if current_view_index != 2:
							new_view_index = 2;
					elif played == 0 and unplayed == 0:
						if current_view_index != 0:
							new_view_index = 0;
					elif played == 0 and unplayed > 0:
						# Fixtures announced, but no games played yet
						if current_view_index != 2:
							new_view_index = 2;
					elif played > 0 and unplayed == 0:
						# All games in this round have been played
						if current_view_index != 1:
							new_view_index = 1;
					else:
						# Round in progress: we want the videprinter
						if current_view_index != 0:
							new_view_index = 0;
			elif teleost_mode > 0:
				if teleost_mode - 1 != current_view_index:
					new_view_index = teleost_mode - 1;
			
		if new_view_index is not None:
			# Change view and force a redraw
			current_view_index = new_view_index;
			if current_view_index in range(0, len(view_list)):
				view_list[current_view_index].restart();
			last_redraw = 0;
			new_view_index = None;

		if time.time() > last_redraw + redraw_interval:
			screen.fill((0, 0, 32, 0));
			if background:
				if not background_scaled:
					# Scale background so that either the width or height is the
					# same size as the screen, and the other dimension is no
					# smaller than the corresponding dimension of the screen
					x_scale_factor = float(screen.get_width()) / float(background.get_width());
					y_scale_factor = float(screen.get_height()) / float(background.get_height());
					scale_factor = max((x_scale_factor, y_scale_factor));
					bg_scaled_width = int(scale_factor * background.get_width());
					bg_scaled_height = int(scale_factor * background.get_height());


					bg_scaled_top = (bg_scaled_height - screen.get_height()) / 2;
					bg_scaled_left = (bg_scaled_width - screen.get_width()) / 2;
					background_scaled = pygame.transform.scale(background, (bg_scaled_width, bg_scaled_height));
					#print "%d,%d" % (bg_scaled_left, bg_scaled_top);
				screen.blit(background_scaled, dest=(0,0), area=(bg_scaled_left, bg_scaled_top, bg_scaled_left + screen.get_width(), bg_scaled_top + screen.get_height()));
			#standings_videprinter.refresh(screen);

			# Use the currently selected view to refresh the screen
			view_list[current_view_index].refresh(screen);
			pygame.display.flip();
			last_redraw = time.time();
		time.sleep(0.1);

		pygame.event.pump();
		event = pygame.event.poll();
		while event.type != pygame.NOEVENT:
			if event.type == pygame.VIDEORESIZE:
				screen_width = event.w;
				screen_height = event.h;
				resized = True;
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_q:
					print "That's all folks!";
					sys.exit(0);
				elif event.key in view_key_map:
					if view_key_map[event.key] < len(view_list):
						new_view_index = view_key_map[event.key];
				elif event.key == pygame.K_t:
					title_bar = not(title_bar);
					pygame.display.get_surface().fill((0, 0, 0));
					pygame.display.flip();
					flags = pygame.RESIZABLE;
					if not title_bar:
						flags |= pygame.NOFRAME;
					screen = pygame.display.set_mode((screen_width, screen_height), flags);
					background_scaled = None;
					last_redraw = 0;
				elif event.key == pygame.K_f:
					if fullscreen:
						screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE);
						fullscreen = False;
						background_scaled = None;
						last_redraw = 0; # force refresh
					else:
						modes = pygame.display.list_modes();
						if not modes:
							print "No display modes available!";
						else:
							mode = max(modes, key=lambda x : x[0] * x[1]);
							screen = pygame.display.set_mode(mode, pygame.NOFRAME | pygame.FULLSCREEN);
							fullscreen = True;
							background_scaled = None;
							last_redraw = 0; # force refresh

			event = pygame.event.poll();
except Exception as e:
	print e;
	print traceback.print_exc();
	print """
	WHOOP WHOOP WHOOP

	GRAEME IS A BELLFACE
""";

	print """Whoops, an unhandled exception occurred. I'm going to exit now. This is probably a bug.""";
	ts = time.strftime("%Y%m%d%H%M%S");
	stacktrace_filename = "stacktrace_" + ts + ".txt";

	try:
		f = open(stacktrace_filename, "w");
		f.write("Teleost version " + teleost_version + "\n");
		f.write(str(e) + "\n");
		traceback.print_exc(file=f);
		f.close();
		print "";
		print "Debug information written to " + stacktrace_filename + ".";
		print "Send that file to Graeme. And call him a bellface.";
	except Exception as e:
		print e;
		print "Another exception occurred while trying to write info about the first one.";
		print "Deary me, things do seem to be going wrong today.";

	print;
	print "Press ENTER to exit...";
	raw_input();
	sys.exit(1);

sys.exit(0);
