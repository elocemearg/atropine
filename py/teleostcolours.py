#!/usr/bin/python

import random

standard_palette = {
        "fixtures_round_name" : (255, 255, 255),
        "fixtures_player_name" : (255, 255, 255),
        "fixtures_unknown_player_name" : (255, 255, 255),
        "fixtures_score" : (255, 255, 255),

        "fixtures_winner_bg" : (0, 255, 0, 64),
        "fixtures_winner_bg_transparent" : (0, 255, 0, 0),

        "fixtures_loser_bg" : (255, 0, 0, 64),
        "fixtures_loser_bg_transparent" : (255, 0, 0, 0),

        "fixtures_draw_bg" : (255, 255, 0, 64),
        "fixtures_draw_bg_transparent" : (255, 255, 0, 0),

        "fixtures_table_bg" : (0, 0, 0, 48),
        "fixtures_table_number_bg" : (0, 0, 255, 128),
        "fixtures_table_number_fg" : (255, 255, 255),

        "videprinter_round" : (255, 128, 64),
        "videprinter_timestamp" : (128, 128, 128),
        "videprinter_score" : (255, 255, 255),
        "videprinter_name_neutral" : (192, 192, 48),
        "videprinter_name_winner" : (0, 192, 0),
        "videprinter_name_loser" : (255, 48, 48),
        "videprinter_superseded" : (128, 128, 128),
        "strikethrough" : (192, 192, 192),

        "standings_column_heading" : (192, 192, 192),
        "standings_division_name" : (32, 255, 32),
        "standings_header_line" : (64, 64, 64),

        "standings_pos" : (255, 255, 0),
        "standings_name" : (255, 255, 255),
        "standings_played" : (0, 128, 128),
        "standings_wins_significant" : (0, 255, 255),
        "standings_wins_insignificant" : (0, 128, 128),
        "standings_points" : (0, 255, 255),
        "standings_withdrawn" : (128, 128, 128),
        
        "table_results_top_row" : (0, 192, 192),
        "table_results_name" : (255, 255, 255),
        "table_results_score" : (255, 255, 255),

        "table_results_winner_bg" : (0, 255, 0, 64),
        "table_results_winner_bg_transparent" : (0, 255, 0, 0),
        "table_results_loser_bg" : (255, 0, 0, 64),
        "table_results_loser_bg_transparent" : (255, 0, 0, 0),
        "table_results_draw_bg" : (255, 255, 0, 64),
        "table_results_draw_bg_transparent" : (255, 255, 0, 0),

        "records_round" : (255, 128, 64),
        "records_name" : (255, 255, 255),
        "records_score" : (255, 255, 255),

        "overachievers_heading" : (255, 255, 255),
        "overachievers_rank" : (255, 255, 0),
        "overachievers_name" : (255, 255, 255),
        "overachievers_div" : (0, 128, 128),
        "overachievers_seed" : (0, 128, 128),
        "overachievers_pos" : (0, 128, 128),
        "overachievers_diff" : (0, 255, 255),

        "finishers_round_name" : (192, 192, 192),
        "finishers_wall_time" : (192, 192, 192),
        "finishers_header_line" : (128, 128, 128),
        "finishers_table_number_bg" : (0, 0, 255, 128),
        "finishers_table_number_fg" : (255, 255, 255),
        "finishers_table_finish_time" : (0, 255, 0),
        "finishers_table_finish_time_diff" : (0, 255, 255),
        "finishers_games_remaining" : (255, 64, 64),

        "tuff_luck_heading" : (224, 224, 224),
        "tuff_luck_rank" : (255, 255, 0),
        "tuff_luck_name" : (255, 255, 255),
        "tuff_luck_tuffness" : (0, 255, 255),

        "title_bg" : (0, 128, 255, 32),
        "title_fg" : (255, 255, 255),
        "videprinter_bg" : (0, 0, 0, 128),
        "standings_results_bg" : (0, 0, 0, 128),

        "table_index_name_bg" : (0, 0, 128, 96),
        "table_index_name_fg" : (255, 255, 255),
        "table_index_table_bg" : (0, 0, 255),
        "table_index_table_fg" : (255, 255, 255),

        "table_index_page_number" : (128, 128, 128)
}

psychedelic_palette = {
        "fixtures_round_name" : (255, 0, 255),
        "fixtures_player_name" : (255, 192, 255),
        "fixtures_unknown_player_name" : (255, 192, 255),
        "fixtures_score" : (255, 96, 24),

        "fixtures_winner_bg" : (0, 255, 0, 128),
        "fixtures_winner_bg_transparent" : (0, 255, 255, 32),

        "fixtures_loser_bg" : (255, 0, 255, 128),
        "fixtures_loser_bg_transparent" : (255, 0, 0, 32),

        "fixtures_draw_bg" : (255, 255, 0, 128),
        "fixtures_draw_bg_transparent" : (255, 255, 0, 32),

        "fixtures_table_bg" : (255, 0, 255, 48),
        "fixtures_table_number_bg" : (255, 69, 0, 128),
        "fixtures_table_number_fg" : (127, 255, 0),

        "videprinter_round" : (255, 255, 0),
        "videprinter_timestamp" : (255, 69, 0),
        "videprinter_score" : (255, 96, 24),
        "videprinter_name_neutral" : (192, 192, 48),
        "videprinter_name_winner" : (0, 192, 64),
        "videprinter_name_loser" : (255, 128, 255),
        "videprinter_bg" : (255, 0, 255, 48),
        "videprinter_superseded" : (128, 128, 128),
        "strikethrough" : (192, 192, 192),

        "standings_column_heading" : (128, 128, 255),
        "standings_division_name" : (32, 255, 32),
        "standings_header_line" : (255, 255, 0),

        "standings_pos" : (255, 0, 255),
        "standings_name" : (0, 255, 255),
        "standings_played" : (0, 128, 128),
        "standings_wins_significant" : (255, 255, 0),
        "standings_wins_insignificant" : (192, 192, 0),
        "standings_points" : (255, 255, 128),
        "standings_withdrawn" : (255, 0, 0),
        
        "table_results_top_row" : (255, 255, 0),
        "table_results_name" : (64, 192, 192),
        "table_results_score" : (255, 96, 24),

        "table_results_winner_bg" : (0, 255, 0, 128),
        "table_results_winner_bg_transparent" : (0, 255, 255, 32),

        "table_results_loser_bg" : (255, 0, 255, 128),
        "table_results_loser_bg_transparent" : (255, 0, 0, 32),

        "table_results_draw_bg" : (255, 255, 0, 128),
        "table_results_draw_bg_transparent" : (255, 255, 0, 32),

        "records_round" : (255, 255, 0),
        "records_name" : (32, 255, 192),
        "records_score" : (255, 96, 24),

        "overachievers_heading" : (255, 255, 0),
        "overachievers_rank" : (255, 0, 255),
        "overachievers_name" : (64, 160, 255),
        "overachievers_div" : (255, 0, 128),
        "overachievers_seed" : (255, 64, 255),
        "overachievers_pos" : (255, 128, 255),
        "overachievers_diff" : (255, 96, 24),

        "finishers_round_name" : (255, 0, 255),
        "finishers_wall_time" : (255, 255, 0),
        "finishers_header_line" : (255, 255, 0),
        "finishers_table_number_bg" : (255, 69, 0, 128),
        "finishers_table_number_fg" : (127, 255, 0),
        "finishers_table_finish_time" : (192, 0, 64),
        "finishers_table_finish_time_diff" : (255, 64, 128),
        "finishers_games_remaining" : (255, 64, 192),

        "tuff_luck_heading" : (255, 255, 0),
        "tuff_luck_rank" : (255, 0, 255),
        "tuff_luck_name" : (64, 160, 255),
        "tuff_luck_tuffness" : (255, 96, 24),

        "title_bg" : (255, 64, 255, 64),
        "title_fg" : (255, 255, 64, 0),
        "standings_results_bg" : (255, 64, 255, 64),

        "table_index_name_bg" : (255, 0, 255, 64),
        "table_index_name_fg" : (255, 255, 255),
        "table_index_table_bg" : (255, 0, 255),
        "table_index_table_fg" : (255, 255, 255),

        "table_index_page_number" : (128, 0, 128)
}

high_contrast_palette = dict(standard_palette)
high_contrast_palette["table_results_winner_bg"] = high_contrast_palette["fixtures_winner_bg"] = (0, 192, 0, 192)
high_contrast_palette["table_results_winner_bg_transparent"] = high_contrast_palette["fixtures_winner_bg_transparent"] = (0, 192, 0, 32)
high_contrast_palette["table_results_loser_bg"] = high_contrast_palette["fixtures_loser_bg"] = (192, 0, 0, 192)
high_contrast_palette["table_results_loser_bg_transparent"] = high_contrast_palette["fixtures_loser_bg_transparent"] = (192, 0, 0, 32)
high_contrast_palette["table_results_draw_bg"] = high_contrast_palette["fixtures_draw_bg"] = (192, 192, 0, 192)
high_contrast_palette["table_results_draw_bg_transparent"] = high_contrast_palette["fixtures_draw_bg_transparent"] = (192, 192, 0, 32)
high_contrast_palette["fixtures_table_bg"] = (0, 0, 0, 96)
high_contrast_palette["fixtures_table_number_bg"] = (0, 0, 192, 192)
high_contrast_palette["finishers_table_number_bg"] = (0, 0, 192, 192)
high_contrast_palette["title_bg"] = (0, 128, 255, 64)

palette = standard_palette

random_palette = dict()
for name in standard_palette:
    random_palette[name] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

pink = dict()
for name in standard_palette:
    if name.endswith("_bg"):
        pink[name] = (192, 0, 128, 64)
    elif name.endswith("_transparent"):
        pink[name] = (128, 0, 128, 0)
    else:
        pink[name] = (255, 128, 255, 255)

palettes_list = [
        ("Standard", standard_palette),
        ("High Contrast", high_contrast_palette),
        ("Psychedelic", psychedelic_palette),
        ("Random", random_palette),
        ("Everything Pink", pink)
]

palettes = dict()
for (name, palette) in palettes_list:
    palettes[name] = palette

def get(name):
    return palette.get(name, (255, 255, 255))

def list_palettes():
    return [ x[0] for x in palettes_list ]

def set_palette(name):
    global palette
    palette = palettes.get(name, standard_palette)
