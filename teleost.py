#!/usr/bin/python

import pygame;
import os;
import sys;
import time;
import traceback;

local_view_switching = False;

view_key_map = {
        pygame.K_F1: 1,
        pygame.K_F2: 2,
        pygame.K_F3: 3,
        pygame.K_F4: 4,
        pygame.K_F5: 5,
        pygame.K_F6: 6,
        pygame.K_F7: 7,
        pygame.K_F8: 8,
        pygame.K_F9: 9,
        pygame.K_F10: 10,
        pygame.K_F12: 0
};

os.chdir(os.path.dirname(os.path.abspath(__file__)));
sys.path.append(os.path.join(os.getcwd(), "py"));

import teleostscreen;
import teleostfetchers;
import teleostcolours;
import countdowntourney;

def make_full_screen_fetcher_view(view_title, view_description, title_text, fetcher, num_lines):
    v = teleostscreen.View(name=view_title, desc=view_description);

    # Add title area and title text
    v.add_view(teleostscreen.ShadedArea(None, "title_bg"), top_pc=0, height_pc=13, left_pc=0, width_pc=100);
    v.add_view(teleostscreen.LabelWidget(title_text, left_pc=6, top_pc=4, height_pc=7, width_pc=100, text_colour_name="title_fg"));
    v.add_view(teleostscreen.TableWidget(fetcher, num_lines), top_pc=15, height_pc=85, left_pc=5, width_pc=90);
    return v;

def draw_banner(surface, position, width, height, text, fg_colour, bg_colour):
    # Draw the banner background...
    banner_background = pygame.Surface((width, height), pygame.SRCALPHA)
    banner_background.fill(bg_colour)
    surface.blit(banner_background, position)

    banner_horiz_padding = width // 50;
    if banner_horiz_padding < 5:
        banner_horiz_padding = 5

    if banner_horiz_padding >= width:
        return

    # Now draw the lettering
    font = teleostscreen.get_sensible_font("sans-serif", height);
    label = teleostscreen.make_text_label(font, text, fg_colour, width - banner_horiz_padding * 2)
    if label.get_width() < width:
        surface.blit(label, (position[0] + (width - label.get_width()) // 2, position[1]))
    else:
        surface.blit(label, position)


def print_help():
    print ""
    print "Teleost key commands"
    print "Note: these only work when the Teleost window has focus."
    print ""
    print "Screen selection"
    print "   F1  Standings only                    F6  Name-to-table Index"
    print "   F2  Standings and Videprinter         F7  Overachievers"
    print "   F3  Standings and Table Results       F8  Tuff Luck"
    print "   F4  Vertical Standings and Results    F9  Notable scores"
    print "   F5  Fixtures                         F10  Fastest finishers"
    print "  F12  Automatic (default)"
    print ""
    print "Screen pages"
    print "    P  Pause/unpause page scrolling   SPACE  Next page"
    print ""
    print "Miscellaneousnesses"
    print "    F  Toggle fullscreen"
    print "    H  Show this help"
    print "    T  Show/hide title bar"
    print "    Q  Quit"
    print ""


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
    short_standings_fetcher = teleostfetchers.StandingsFetcher(tourney, True)
    team_score_fetcher = teleostfetchers.TeamScoreFetcher(tourney);
    videprinter_fetcher = teleostfetchers.VideprinterFetcher(tourney);
    table_results_fetcher = teleostfetchers.TableResultsFetcher(tourney);
    short_table_results_fetcher = teleostfetchers.TableResultsFetcher(tourney, True);
    highest_winning_scores_fetcher = teleostfetchers.HighestWinningScoresFetcher(tourney);
    highest_losing_scores_fetcher = teleostfetchers.HighestLosingScoresFetcher(tourney);
    highest_joint_scores_fetcher = teleostfetchers.HighestJointScoresFetcher(tourney);
    overachievers_fetcher = teleostfetchers.OverachieversFetcher(tourney);
    quickest_finishers_fetcher = teleostfetchers.QuickestFinishersFetcher(tourney);
    current_round_fixtures_fetcher = teleostfetchers.CurrentRoundFixturesFetcher(tourney);
    tuff_luck_fetcher = teleostfetchers.TuffLuckFetcher(tourney);
    table_index_fetcher = teleostfetchers.TableIndexFetcher(tourney)

    #fontfilename = "/usr/share/fonts/truetype/futura/Futura Condensed Bold.ttf";

    standings_widget = teleostscreen.TableWidget(standings_fetcher, 9, scroll_interval=10);
    vertical_standings_widget = teleostscreen.TableWidget(short_standings_fetcher, 13, scroll_interval=12)
    tall_standings_widget = teleostscreen.TableWidget(standings_fetcher, 13, scroll_interval=12);
    team_score_widget = teleostscreen.TableWidget(team_score_fetcher, 1, scroll_interval=5)

    standings_only = teleostscreen.View(name="Standings", desc="Just the current standings table.")
    standings_only.add_view(tall_standings_widget, top_pc=5, height_pc=90, left_pc=0, width_pc=95)

    standings_videprinter = teleostscreen.View(name="Standings / Videprinter", desc="Standings table taking up most of the screen, with latest results displayed on a scrolling window below.");

    standings_videprinter.add_view(standings_widget, top_pc=5, height_pc=65, left_pc=0, width_pc=95);
    standings_videprinter.add_view(teleostscreen.ShadedArea(None, "videprinter_bg"), top_pc=72, height_pc=30, left_pc=0, width_pc=100);
    standings_videprinter.add_view(team_score_widget, top_pc=5, height_pc=7, left_pc=5, width_pc=20);
    standings_videprinter.add_view(teleostscreen.VideprinterWidget(videprinter_fetcher, 4), top_pc=73, height_pc=25, left_pc=2, width_pc=100);

    standings_results = teleostscreen.View(name="Standings / Table Results", desc="Standings table taking up most of the screen, with this round's fixtures and results displayed at the bottom.");
    standings_results.add_view(standings_widget, top_pc=5, height_pc=65, left_pc=0, width_pc=95);
    standings_results.add_view(teleostscreen.ShadedArea(None, "standings_results_bg"), top_pc=72, height_pc=30, left_pc=0, width_pc=100);
    standings_results.add_view(teleostscreen.TableWidget(table_results_fetcher, 4, scroll_interval=5, scroll_sideways=True), top_pc=73, height_pc=26, left_pc=0, width_pc=100);
    standings_results.add_view(team_score_widget, top_pc=5, height_pc=7, left_pc=5, width_pc=20);
    
    standings_results_vert = teleostscreen.View(name="Standings / Table Results (vertical)", desc="Standings table on the left half of the screen, this round's fixtures and results on the right.")
    standings_results_vert.add_view(vertical_standings_widget, top_pc=5, height_pc=90, left_pc=2, width_pc=46)
    standings_results_vert.add_view(teleostscreen.TableWidget(short_table_results_fetcher, 15, scroll_interval=12), top_pc=5, height_pc=90, left_pc=52, width_pc=46)
    standings_results_vert.add_view(team_score_widget, top_pc=5, height_pc=7, left_pc=5, width_pc=20);

    notables = teleostscreen.TimedViewCycler(name="Records", desc="Highest winning scores, losing scores and combined scores.");

    for (text, fetcher) in [
            ("Highest winning scores", highest_winning_scores_fetcher),
            ("Highest losing scores", highest_losing_scores_fetcher),
            ("Highest joint scores", highest_joint_scores_fetcher)
        ]:
        v = teleostscreen.View();
        v.add_view(teleostscreen.ShadedArea(None, "title_bg"), top_pc=0, height_pc=13, left_pc=0, width_pc=100);
        v.add_view(teleostscreen.LabelWidget(text, left_pc=6, top_pc=4, height_pc=7, width_pc=100, text_colour_name="title_fg"));
        v.add_view(teleostscreen.TableWidget(fetcher, 12), top_pc=15, height_pc=85, left_pc=5, width_pc=90);
        notables.add_view(v, 10);
    
    overachievers = make_full_screen_fetcher_view("Overachievers", "Display table of players ranked by how high they rank above their seed.", "Overachievers", overachievers_fetcher, 12);

    quickest_finishers = make_full_screen_fetcher_view("Fastest Finishers", "An excellent way to highlight which tables are taking too long to finish their games.", "Fastest Finishing Tables", quickest_finishers_fetcher, 12);

    tuff_luck = make_full_screen_fetcher_view("Tuff Luck", "Players who have lost three or more games ordered by the sum of their three lowest losing margins.", "Tuff Luck", tuff_luck_fetcher, 12);

    fixtures = teleostscreen.View(name="Fixtures", desc="Display all fixtures in the current round, using the whole screen to do it.");
    fixtures.add_view(teleostscreen.PagedFixturesWidget(current_round_fixtures_fetcher, num_lines=13, scroll_interval=10), top_pc=0, left_pc=0, width_pc=100, height_pc=100);
    fixtures.add_view(team_score_widget, top_pc=1, height_pc=8, left_pc=69, width_pc=30);

    table_index = teleostscreen.View(name="Table Index", desc="Display player names and which table they should be on, sorted by player name.")
    table_index.add_view(teleostscreen.TableIndexWidget(table_index_fetcher), top_pc=3, left_pc=5, width_pc=90, height_pc=94)

    view_list = [
            standings_only,
            standings_videprinter,
            standings_results,
            standings_results_vert,
            fixtures,
            table_index,
            overachievers,
            tuff_luck,
            notables,
            quickest_finishers,
    ];
    standings_only_view_index = 0
    standings_videprinter_view_index = 1
    standings_results_view_index = 2
    standings_results_vert_view_index = 3
    fixtures_view_index = 4
    table_index_view_index = 5
    overachievers_view_index = 6
    tuff_luck_view_index = 7
    notables_view_index = 8
    quickest_finishers_view_index = 9

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
    banner_height_ratio = 0.1
    banner_height = int(screen_height * banner_height_ratio)
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
    bumps = 0
    previous_foreground = None
    paused = False
    redraw_overlay = False

    print_help()

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
            teleost_palette = tourney.get_teleost_colour_palette()
            teleost_animate_scroll = tourney.get_teleost_animate_scroll()
            teleostcolours.set_palette(teleost_palette)
            last_mode_check = time.time();
	    banner_text = tourney.get_banner_text()
            if teleost_mode == 0:
                auto_use_vertical = tourney.get_auto_use_vertical();
                auto_use_table_index = tourney.get_auto_use_table_index()
                r = tourney.get_current_round()
                if not r:
                    if current_view_index != standings_videprinter_view_index:
                        new_view_index = standings_videprinter_view_index;
                else:
                    round_no = r["num"]
                    largest_table_size = tourney.get_largest_table_game_count(round_no)
                    (played, unplayed) = tourney.get_played_unplayed_counts(round_no=round_no);
                    if played == 0 and unplayed == 0:
                        if current_view_index != standings_videprinter_view_index:
                            new_view_index = standings_videprinter_view_index;
                    elif played == 0 and unplayed > 0:
                        # Fixtures announced, but no games played yet
                        if auto_use_table_index:
                            # Display table index if user has requested that
                            if current_view_index != table_index_view_index:
                                new_view_index = table_index_view_index
                        else:
                            # Otherwise display fixtures
                            if current_view_index != fixtures_view_index:
                                new_view_index = fixtures_view_index;
                    elif played > 0 and unplayed == 0:
                        # All games in this round have been played - we
                        # want the standings and results screen, but if
                        # we don't have three games to a table or if 
                        # auto_use_vertical is set then we want the vertical
                        # standings and results screen.
                        if largest_table_size <= 3 and not(auto_use_vertical):
                            if current_view_index != standings_results_view_index:
                                new_view_index = standings_results_view_index;
                        else:
                            if current_view_index != standings_results_vert_view_index:
                                new_view_index = standings_results_vert_view_index
                    else:
                        # Round in progress: we want the videprinter
                        if current_view_index != standings_videprinter_view_index:
                            new_view_index = standings_videprinter_view_index;
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

        if time.time() > last_redraw + redraw_interval or bumps > 0:
            background_screen = pygame.Surface(screen.get_size())
            background_screen.fill((0, 0, 32, 0));
            if background:
                if not background_scaled:
                    # Scale background so that either the width or height is the
                    # same size as the screen, and the other dimension is no
                    # smaller than the corresponding dimension of the screen
                    x_scale_factor = float(background_screen.get_width()) / float(background.get_width());
                    y_scale_factor = float(background_screen.get_height()) / float(background.get_height());
                    scale_factor = max((x_scale_factor, y_scale_factor));
                    bg_scaled_width = int(scale_factor * background.get_width());
                    bg_scaled_height = int(scale_factor * background.get_height());


                    bg_scaled_top = (bg_scaled_height - background_screen.get_height()) / 2;
                    bg_scaled_left = (bg_scaled_width - background_screen.get_width()) / 2;
                    background_scaled = pygame.transform.scale(background, (bg_scaled_width, bg_scaled_height));
                    #print "%d,%d" % (bg_scaled_left, bg_scaled_top);
                background_screen.blit(background_scaled, dest=(0,0), area=(bg_scaled_left, bg_scaled_top, bg_scaled_left + screen.get_width(), bg_scaled_top + screen.get_height()));
            #standings_videprinter.refresh(screen);
            
            new_foreground = pygame.Surface(screen.get_size(), flags=pygame.SRCALPHA)
            if banner_text:
                new_foreground = pygame.Surface((screen.get_width(), screen.get_height() - banner_height), flags=pygame.SRCALPHA)
                foreground_position = (0, banner_height)
                banner_surface = pygame.Surface((screen.get_width(), banner_height), flags=pygame.SRCALPHA)
                draw_banner(banner_surface, (0, 0), banner_surface.get_width(), banner_surface.get_height(), banner_text, teleostcolours.get("banner_fg"), teleostcolours.get("banner_bg"))
            else:
                new_foreground = pygame.Surface(screen.get_size(), flags=pygame.SRCALPHA)
                foreground_position = (0, 0)
                banner_surface = None

            new_foreground.fill((0, 0, 0, 0))

            # If we've received a key event to bump the page, bump every view
            # on this page
            while bumps > 0:
                view_list[current_view_index].bump(None)
                bumps -= 1

            # Use the currently selected view to refresh the screen
            transition_instructions = view_list[current_view_index].refresh(new_foreground);

            if teleost_animate_scroll and transition_instructions and previous_foreground is not None and previous_foreground.get_rect() == new_foreground.get_rect():
                scroll_time = 0.4
                num_scroll_frames = 20
                for scroll_frame in range(num_scroll_frames):
                    # For everything not in the scrolling region, paint the
                    # previous screen if we're less than half way through the
                    # scroll, and the new screen otherwise
                    screen.blit(background_screen, (0, 0))
                    if banner_surface:
                        screen.blit(banner_surface, (0, 0))
                    if scroll_frame < num_scroll_frames / 2:
                        screen.blit(previous_foreground, foreground_position)
                    else:
                        screen.blit(new_foreground, foreground_position)

                    # foreground_window: that area of the screen that isn't
                    # the banner, i.e. the bit that all the views have been
                    # scribbling on
                    foreground_window = screen.subsurface((foreground_position[0], foreground_position[1], new_foreground.get_width(), new_foreground.get_height()))
                    background_window = background_screen.subsurface((foreground_position[0], foreground_position[1], new_foreground.get_width(), new_foreground.get_height()))

                    # Paint the background back over everything that's going
                    # to be shown scrolling
                    for ti in transition_instructions:
                        foreground_window.blit(background_window, ti.get_rect(), ti.get_rect())

                    # Tell the scroll instruction to draw the scroll at the
                    # given progress point
                    for ti in transition_instructions:
                        ti.draw_scroll_frame(foreground_window, previous_foreground, new_foreground, float(scroll_frame + 1) / num_scroll_frames)

                    # Update the display
                    pygame.display.flip()
                    time.sleep(scroll_time / num_scroll_frames)

            screen.blit(background_screen, (0, 0))
            if banner_surface:
                screen.blit(banner_surface, (0, 0))
            screen.blit(new_foreground, foreground_position)
                
            previous_foreground = new_foreground

            if paused:
                paused_label = teleostscreen.make_text_label(teleostscreen.get_sensible_font("sans-serif", screen.get_height() / 30), " || ", (255, 255, 255))
                screen.blit(paused_label, (screen.get_width() - paused_label.get_width(), 2))
            pygame.display.flip()
            last_redraw = time.time();

        time.sleep(0.1);

        pygame.event.pump();
        event = pygame.event.poll();
        while event.type != pygame.NOEVENT:
            if event.type == pygame.VIDEORESIZE:
                screen_width = event.w;
                screen_height = event.h;
                banner_height = int(screen_height * banner_height_ratio)
                resized = True;
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    print "That's all folks!";
                    sys.exit(0);
                elif event.key == pygame.K_h:
                    print_help()
                elif event.key == pygame.K_p:
                    if paused:
                        for v in view_list:
                            v.unpause()
                        paused = False
                        print "Unpaused"
                    else:
                        for v in view_list:
                            v.pause()
                        paused = True
                        print "Paused"
                    last_redraw = 0
                elif event.key in view_key_map:
                    teleost_mode = view_key_map[event.key];
                    last_redraw = 0
                    last_mode_check = 0
                    tourney.set_teleost_mode(teleost_mode)
                elif event.key == pygame.K_t:
                    title_bar = not(title_bar);
                    pygame.display.get_surface().fill((0, 0, 0));
                    pygame.display.flip();
                    flags = pygame.RESIZABLE;
                    if not title_bar:
                        flags |= pygame.NOFRAME;
                    screen = pygame.display.set_mode((screen_width, screen_height), flags);
                    banner_height = int(screen.get_height() * banner_height_ratio)
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
                            banner_height = int(screen.get_height() * banner_height_ratio)
                            fullscreen = True;
                            background_scaled = None;
                            last_redraw = 0; # force refresh
                elif event.key == pygame.K_SPACE:
                    bumps += 1

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
