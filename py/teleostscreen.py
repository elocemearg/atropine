#!/usr/bin/python

import sys;
import os;
import pygame;
import time;
import sqlite3;
import countdowntourney;
import traceback;
import teleostcolours;
import math

draw_table_lines = False;

ALIGN_LEFT = 0;
ALIGN_CENTRE = 1;
ALIGN_RIGHT = 2;

def limit_label_width(label, max_width):
    if label.get_width() <= max_width:
        return label;
    try:
        return pygame.transform.smoothscale(label, (max_width, label.get_height()));
    except:
        return pygame.transform.scale(label, (max_width, label.get_height()));

def make_text_label(font, text, text_colour, width_limit=None, outline_colour=(0,0,0)):
    outline_size = font.get_height() / 20
    outline_size = min(max(outline_size, 1), 3)

    text_label = font.render(text, 1, text_colour)
    shadow_label = font.render(text, 1, outline_colour)

    if width_limit:
        text_label = limit_label_width(text_label, width_limit)
        shadow_label = limit_label_width(shadow_label, width_limit)

    label = pygame.Surface((text_label.get_width() + 2 * outline_size, text_label.get_height() + 2 * outline_size), pygame.SRCALPHA)

    # Draw a smudged-about shadow of the text, which is a black image of the
    # text copied to all surrounding positions within an outline_size-pixel
    # radius.
    if text and outline_size > 0:
        for dy in range(0, outline_size * 2 + 1):
            smudge_width = outline_size - abs(outline_size - dy)
            for dx in range(0, outline_size * 2 + 1):
                if abs(outline_size - dx) ** 2 + abs(outline_size - dy) ** 2 <= outline_size ** 2:
                    label.blit(shadow_label, (dx, dy))

    # Then drop the text inside it
    label.blit(text_label, (outline_size, outline_size))

    return label

def shade_area(surface, rect, colour):
    tmp_surface = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA);
    tmp_surface.blit(surface, (0, 0), area=rect);
    shade = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA);
    shade.fill(colour);
    tmp_surface.blit(shade, (0, 0));
    surface.blit(tmp_surface, (rect[0], rect[1]));

def surface_merge(dest, src, dest_pos, src_area):
    # Copy src_area of src onto dest at dest_pos, respecting transparency of
    # src.
    tmp = pygame.Surface((src_area[2], src_area[3]), pygame.SRCALPHA);
    tmp.blit(dest, (0, 0), (dest_pos[0], dest_pos[1], src_area[2], src_area[3]));
    tmp.blit(src, (0, 0));
    dest.blit(tmp, dest_pos);

def shade_area_horiz_gradient(surface, rect, start_colour, end_colour):
    (r, g, b, a) = start_colour;
    width = rect[2];
    r_step = float(end_colour[0] - r) / float(width);
    g_step = float(end_colour[1] - g) / float(width);
    b_step = float(end_colour[2] - b) / float(width);
    a_step = float(end_colour[3] - a) / float(width);

    tmp_surface = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA);
    tmp_surface.blit(surface, (0, 0), area=rect);
    shade = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA);

    step_size = 5;
    for x in range(rect[0], rect[0] + width, step_size):
        shade.fill((int(r), int(g), int(b), int(a)), rect=(x - rect[0], 0, min(step_size, rect[0] + width - x), rect[3]));
        #print r,g,b,a,x;
        r += r_step * step_size;
        g += g_step * step_size;
        b += b_step * step_size;
        a += a_step * step_size;
        (r,g,b,a) = map(lambda y : min(255, max(y, 0)), (r,g,b,a));
    tmp_surface.blit(shade, (0, 0));
    surface.blit(tmp_surface, (rect[0], rect[1]));

def get_sensible_font(font_name, desired_line_size):
    low = 10;
    high = 200;
    #font_name = "/usr/share/fonts/truetype/futura/Futura Bold.ttf";

    # On Windows, fonts tend to appear slightly larger for some reason
    if os.name == "nt":
        desired_line_size *= 0.8;

    while True:
        size = (low + high) / 2;
        font = pygame.font.SysFont(font_name, size);
        if font.get_linesize() == desired_line_size:
            break;
        elif font.get_linesize() < desired_line_size:
            low = size + 1;
        else:
            high = size - 1;
        if low > high:
            size = high;
            break;
    font = pygame.font.SysFont(font_name, size);
    return font;

use_dot_cache = False
dot_cache = dict()

def make_team_dot(width, height, colour):
    if use_dot_cache:
        dot_surface = dot_cache.get((width, height, colour))
        if dot_surface:
            return dot_surface

    # Draw a dot in the centre of a height*width rectangle
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    if height >= width:
        dot_width = int(0.5 * width)
        dot_height = dot_width
        x = (width - dot_width) / 2
        y = (height - dot_height) / 2
    else:
        dot_height = int(0.5 * height)
        dot_width = dot_height
        x = (width - dot_width) / 2
        y = (height - dot_height) / 2

    start_alpha = 0
    end_alpha = 255
    for corner_x in range(x, x + dot_width / 2):
        corner_y = y + corner_x - x
        sq_width = dot_width - (corner_x - x) * 2
        sq_height = sq_width
        alpha = int(start_alpha + float(corner_x - x) * float(end_alpha - start_alpha) / float(dot_width / 2))
        alpha_colour = (colour[0], colour[1], colour[2], alpha)
        surface.fill(alpha_colour, pygame.Rect(corner_x, corner_y, sq_width, sq_height))

    if use_dot_cache:
        dot_cache[(width, height, colour)] = surface
    return surface

def sigmoid(t):
    return 1.0 / (1.0 + math.exp(-t))
    
class ScrollInstruction(object):
    SCROLL_UP = 0
    SCROLL_LEFT = 1

    def __init__(self, rect, direction=SCROLL_UP):
        self.rect = rect
        self.direction = direction

    def get_rect(self):
        return self.rect

    def draw_scroll_frame(self, surface, original_surface, new_surface, scroll_progress):
        if self.direction == ScrollInstruction.SCROLL_UP:
            scroll_length_max = self.rect.height
        else:
            scroll_length_max = self.rect.width

        # We want the scroll to start slow, speed up in the middle and slow
        # down as it comes to an end, so we'll use a sigmoid function,
        # S(t) = 1 / (1 + e^-t)

        # Increase sigmoid_max if you want more of the activity to be in the
        # middle of the transition time, decrease it if you want it to be
        # more linear.
        sigmoid_max = 5

        # Increase sigmoid_centre if you want most of the scroll to happen
        # towards the end of the transition time (i.e. a slow start, a fast
        # finish), and decrease it if you want most of it to happen at the
        # start.
        sigmoid_centre = 0.5

        scroll_length = int(scroll_length_max * sigmoid((scroll_progress - sigmoid_centre) * sigmoid_max * 2))
        if self.direction == ScrollInstruction.SCROLL_UP:
            surface.blit(original_surface, self.rect, (self.rect.left, self.rect.top + scroll_length, self.rect.width, self.rect.height - scroll_length))
            surface.blit(new_surface, (self.rect.left, self.rect.top + self.rect.height - scroll_length), (self.rect.left, self.rect.top, self.rect.width, scroll_length))
        else:
            surface.blit(original_surface, self.rect, (self.rect.left + scroll_length, self.rect.top, self.rect.width - scroll_length, self.rect.height))
            surface.blit(new_surface, (self.rect.left + self.rect.width - scroll_length, self.rect.top), (self.rect.left, self.rect.top, scroll_length, self.rect.height))

    def transform(self, x, y):
        self.rect.x += x
        self.rect.y += y

class VideprinterScrollInstruction(ScrollInstruction):
    def __init__(self, rect, animate_from_y):
        self.rect = rect
        self.animate_from_y = animate_from_y

    def transform(self, x, y):
        self.rect.x += x
        self.rect.y += y

    def get_rect(self):
        return self.rect

    def draw_scroll_frame(self, surface, original_surface, new_surface, scroll_progress):
        # For the first half of the progress, we'll scroll the videprinter up.
        # For the second half, we'll reveal the new entries.
        
        shift_up_progress = scroll_progress * 2
        if shift_up_progress > 1.0:
            shift_up_progress = 1.0

        sigmoid_max = 5
        sigmoid_centre = 0.5

        if shift_up_progress < 1.0:
            scroll_length_max = self.rect.height - self.animate_from_y
            scroll_length = int(scroll_length_max * sigmoid((shift_up_progress - sigmoid_centre) * sigmoid_max * 2))
            surface.blit(original_surface, self.rect, (self.rect.left, self.rect.top + scroll_length, self.rect.width, self.rect.height - scroll_length))
        else:
            surface.blit(new_surface, self.rect, (self.rect.left, self.rect.top, self.rect.width, self.animate_from_y))

        if scroll_progress >= 0.5:
            wipe_right_progress = (scroll_progress - 0.5) * 2
            wipe_right_px = int(self.rect.width * wipe_right_progress)
            surface.blit(new_surface, (self.rect.left, self.rect.top + self.animate_from_y), (self.rect.left, self.rect.top + self.animate_from_y, wipe_right_px, self.rect.height - self.animate_from_y))

class View(object):
    def __init__(self, name="", desc=""):
        self.sub_views = [];
        self.name = name;
        self.desc = desc;

    def get_name(self):
        return self.name;
    
    def get_description(self):
        return self.desc;
    
    def add_view(self, sub_view, left_pc=0, top_pc=0, width_pc=100, height_pc=100):
        self.sub_views.append((sub_view, top_pc, left_pc, height_pc, width_pc));
    
    def restart(self):
        for v in self.sub_views:
            v[0].restart();
    
    def refresh(self, surface):
        transition_instructions = []
        for (sub_view, top_pc, left_pc, height_pc, width_pc) in self.sub_views:
            top_px = surface.get_height() * top_pc / 100;
            left_px = surface.get_width() * left_pc / 100;
            height_px = surface.get_height() * height_pc / 100;
            width_px = surface.get_width() * width_pc / 100;
            if width_px >= surface.get_width() - left_px:
                width_px = surface.get_width() - left_px - 1;
            if height_px >= surface.get_height() - top_px:
                height_px = surface.get_height() - top_px - 1;
            sub_surface = surface.subsurface((left_px, top_px, width_px, height_px));
            #sub_surface = pygame.Surface((width_px, height_px), flags=pygame.SRCALPHA);
            #sub_surface.fill((0, 0, 0, 0));
            ti = sub_view.refresh(sub_surface);
            if ti:
                ti.transform(left_px, top_px)
                transition_instructions.append(ti)
            #surface.blit(sub_surface, (left_px, top_px));
        return transition_instructions

    def bump(self, surface):
        for (sub_view, a, b, c, d) in self.sub_views:
            sub_view.bump(None)
        if surface:
            self.refresh(self, surface)

class TimedViewCycler(View):
    def __init__(self, name="", desc="", default_interval=10):
        self.sub_views = [];
        self.default_interval = default_interval;
        self.current_view_index = 0;
        self.last_change = time.time();
        self.name = name;
        self.desc = desc;
    
    def get_name(self):
        return self.name;

    def restart(self):
        self.last_change = time.time();
        self.current_view_index = 0;
    
    def get_description(self):
        return self.desc;

    def add_view(self, sub_view, wait_interval=None):
        if wait_interval is None:
            wait_interval = self.default_interval;
        self.sub_views.append((sub_view, wait_interval));
    
    def refresh(self, surface):
        if self.current_view_index >= len(self.sub_views):
            self.current_view_index = len(self.sub_views) - 1;
        if self.current_view_index < 0:
            self.current_view_index = 0;
        if len(self.sub_views) == 0:
            return [];

        previous_view_index = self.current_view_index
        (view, interval) = self.sub_views[self.current_view_index];
        if self.last_change + interval <= time.time():
            self.current_view_index = (self.current_view_index + 1) % len(self.sub_views);
            self.last_change = time.time();
            (view, interval) = self.sub_views[self.current_view_index];

        view.refresh(surface);
        if self.current_view_index != previous_view_index:
            return [ScrollInstruction(surface.get_rect(), ScrollInstruction.SCROLL_LEFT)]
        else:
            return []

    def bump(self, surface):
        self.last_change = 0
        if surface:
            self.refresh(surface)

class PixelLength(object):
    def __init__(self, value):
        self.value = value;
    
    def get_width_px(self, surface):
        return self.value;

    def get_height_px(self, surface):
        return self.value;

class PercentLength(object):
    def __init__(self, pc):
        self.pc = pc;
    
    def get_width_px(self, surface):
        return surface.get_width() * self.pc / 100;
    
    def get_height_px(self, surface):
        return surface.get_height() * self.pc / 100;

class LineStyle(object):
    def __init__(self, colour, width_px):
        self.colour = colour;
        self.width_px = width_px;
    
    def get_colour(self):
        return self.colour;
    
    def get_width_px(self):
        return self.width_px;

class RowValue(object):
    def __init__(self, text, width, text_colour=(255,255,255), alignment=ALIGN_LEFT, row_padding=None, font=None, hgradientpair=None, bg_colour=None):
        self.text = text;
        self.width = width;
        self.text_colour = pygame.Color(text_colour[0], text_colour[1], text_colour[2], 255);
        self.right_aligned = (alignment == ALIGN_RIGHT);
        self.centre_aligned = (alignment == ALIGN_CENTRE);
        if hgradientpair:
            self.left_colour = hgradientpair[0];
            self.right_colour = hgradientpair[1];
        else:
            self.left_colour = None;
            self.right_colour = None;
        self.bg_colour = bg_colour;
        if row_padding is None:
            self.row_padding = PercentLength(2.5);
        else:
            self.row_padding = row_padding;
        self.font = font;
    
    def get_text(self):
        return self.text;

    def get_row_padding_px(self, surface):
        return self.row_padding.get_width_px(surface);

    def get_width_px(self, surface):
        if self.width is None:
            return None;
        else:
            return self.width.get_width_px(surface);
    
    def get_text_colour(self):
        return self.text_colour;

    def is_right_aligned(self):
        return bool(self.right_aligned);
    
    def is_centre_aligned(self):
        return bool(self.centre_aligned);
    
    def get_font(self, default_font=None):
        if self.font is None:
            return default_font;
        else:
            return self.font;
    
    def draw(self, surface, default_font, y, x, row_height_px):
        return self.draw_aux(surface, self.get_text(), default_font, y, x, row_height_px);

    def draw_aux(self, surface, text, default_font, y, x, row_height_px):
        font = self.get_font(default_font);
        width_px = self.get_width_px(surface);
        row_pad_px = int(self.get_row_padding_px(surface));
        shade_spacing = int(row_height_px * 0.1);

        if width_px is not None:
            width_px = int(width_px);

        if width_px is not None and row_pad_px >= width_px:
            row_pad_px = 0;

        if width_px is None:
            label = make_text_label(font, text, self.get_text_colour())
        else:
            label = make_text_label(font, text, self.get_text_colour(), width_px - row_pad_px)

        if width_px is not None and self.is_right_aligned():
            drawn_width = width_px;
            if label.get_width() < width_px:
                label_start_x = x + width_px - label.get_width() - row_pad_px / 2;
            else:
                label_start_x = x;
        elif width_px is not None and self.is_centre_aligned():
            drawn_width = width_px;
            if label.get_width() < width_px:
                label_start_x = x + (width_px - label.get_width()) / 2;
            else:
                label_start_x = x;
        else:
            label_start_x = x + row_pad_px / 2;
            if width_px is None:
                drawn_width = label.get_width() + row_pad_px;
            else:
                drawn_width = width_px;

        if self.bg_colour:
            shade_area(surface, (x + shade_spacing, y + shade_spacing, drawn_width - shade_spacing * 2, row_height_px - shade_spacing * 2), self.bg_colour);
        if self.left_colour and self.right_colour:
            shade_area_horiz_gradient(surface, (x + shade_spacing, y + shade_spacing, drawn_width - shade_spacing * 2, row_height_px - shade_spacing * 2), self.left_colour, self.right_colour);

        if width_px is None:
            src_area = None;
        else:
            label_draw_width_max = width_px - row_pad_px / 2;
            src_area = (0, 0, label_draw_width_max, label.get_height());

        # Correct curious placement of text on Windows
        if os.name == "nt":
            text_y = int(y + 0.15 * row_height_px);
        else:
            text_y = y;

        surface.blit(label, (label_start_x, text_y), area=src_area);

        if draw_table_lines:
            pygame.draw.rect(surface, pygame.Color(64, 64, 64), pygame.Rect(x, y, drawn_width, row_height_px), 1);

        return drawn_width;

class RowValueTeamDot(object):
    def __init__(self, width, fgcolour, bgcolour=None):
        self.width = width
        self.fgcolour = fgcolour
        self.bgcolour = bgcolour

    def get_width_px(self, surface):
        if self.width is None:
            return None;
        else:
            return self.width.get_width_px(surface);

    def get_text(self):
        return "."

    def get_text_colour(self):
        return self.fgcolour

    def draw(self, surface, default_font, y, x, row_height_px):
        label = make_team_dot(self.width.get_width_px(surface), row_height_px, self.fgcolour)
        if self.bgcolour is not None:
            surface.fill(self.bgcolour, pygame.Rect(x, y, self.width.get_width_px(surface), row_height_px))
        surface.blit(label, (x, y))
        return label.get_width()


class TableRow(object):
    def __init__(self):
        self.values = [];
        self.top_border = None;
        self.left_border = None;
        self.right_border = None;
        self.bottom_border = None;
        self.videprinter_seq = 0
        self.strikethrough = False
    
    def append_value(self, value):
        self.values.append(value);
    
    def __getitem__(self, i):
        return self.values[i];
    
    def __len__(self):
        return len(self.values);
    
    def set_videprinter_seq(self, seq):
        self.videprinter_seq = seq
    
    def get_videprinter_seq(self):
        return self.videprinter_seq
    
    def set_strikethrough(self, value):
        self.strikethrough = value

    def draw(self, surface, default_font, y, row_height_px):
        x = 0;
        for value in self.values:
            x += value.draw(surface, default_font, y, x, row_height_px);

        border_list = [];
        border_list.append((self.top_border, 0, y, surface.get_width() - 1, y));
        border_list.append((self.right_border, surface.get_width() - 1, y, surface.get_width() - 1, y + row_height_px - 1));
        border_list.append((self.bottom_border, 0, y + row_height_px - 1, surface.get_width() - 1, y + row_height_px - 1));
        border_list.append((self.left_border, 0, y, 0, y + row_height_px - 1));
        for (border, x0, y0, x1, y1) in border_list:
            if border:
                #print "drawing (%d,%d) to (%d,%d)" % (x0, y0, x1, y1);
                pygame.draw.line(surface, border.get_colour(), (x0, y0), (x1, y1), border.get_width_px());

        if self.strikethrough:
            pygame.draw.line(surface, teleostcolours.get("strikethrough"), (0, y + row_height_px / 2), (min(surface.get_width() - 1, x + row_height_px / 2), y + row_height_px / 2), max(2, row_height_px / 8))

    
    def set_border(self, top_border=None, right_border=None, bottom_border=None, left_border=None):
        self.top_border = top_border;
        self.bottom_border = bottom_border;
        self.left_border = left_border;
        self.right_border = right_border;
    
    @staticmethod
    def concat_rows(rowlist):
        bigrow = TableRow();
        for row in rowlist:
            if row is None:
                continue;
            for value in row.values:
                bigrow.append_value(value);
        return bigrow;
            
class Widget(object):
    def restart(self):
        pass;
    
    def refresh(self):
        return None

    def bump(self, surface):
        return

class VideprinterWidget(Widget):
    def __init__(self, table_fetcher, num_rows, default_font_name="sans-serif"):
        self.table_fetcher = table_fetcher;
        self.default_font_name = default_font_name;
        self.num_rows = num_rows;
        self.current_rows = [];
        self.latest_seq_drawn = -1;
        self.num_refreshes = 0;
    
    def restart(self):
        self.num_refreshes = 0
        self.latest_seq_drawn = -1

    def refresh(self, surface):
        try:
            header_row = self.table_fetcher.fetch_header_row();

            # Work out how many data rows we want
            if header_row is None:
                data_rows_to_fetch = self.num_rows;
            else:
                data_rows_to_fetch = self.num_rows - 1;

            row_height_px = surface.get_height() / self.num_rows;

            font = get_sensible_font(self.default_font_name, row_height_px);

            self.current_rows = self.table_fetcher.fetch_data_rows(data_rows_to_fetch);
            if len(self.current_rows) > data_rows_to_fetch:
                self.current_rows = self.current_rows[-data_rows_to_fetch:]

            # Draw the header row if necessary
            pos_y = 0;
            if header_row:
                header_row.draw(surface, font, pos_y, row_height_px);
                pos_y += row_height_px;

            # If there are fewer than num_rows rows, we should leave space
            # at the top, not at the bottom.
            if len(self.current_rows) < self.num_rows:
                pos_y += row_height_px * (self.num_rows - len(self.current_rows))

            animate_from_y = None

            for row in self.current_rows:
                row.draw(surface, font, pos_y, row_height_px);
                if self.num_refreshes > 0 and self.latest_seq_drawn < row.get_videprinter_seq():
                    if animate_from_y is None:
                        animate_from_y = pos_y
                if row.get_videprinter_seq() > self.latest_seq_drawn:
                    self.latest_seq_drawn = row.get_videprinter_seq()
                pos_y += row_height_px;

            self.num_refreshes += 1;

            if animate_from_y is not None:
                return VideprinterScrollInstruction(surface.get_rect(), animate_from_y)
            else:
                return None
        except countdowntourney.TourneyException as e:
            traceback.print_exc();
            surface.fill((255, 0, 0, 255));
        except sqlite3.Error as e:
            traceback.print_exc();
            surface.fill((255, 128, 0, 255));
        return None


class TableWidget(Widget):
    def __init__(self, table_fetcher, num_rows, default_font_name="sans-serif", scroll_interval=10, scroll_sideways=False):
        self.table_fetcher = table_fetcher;
        self.scroll_interval = scroll_interval;
        self.last_scroll_time = time.time();
        self.current_row = 0;
        self.num_rows_on_screen = num_rows;
        self.default_font_name = default_font_name;
        if scroll_sideways:
            self.scroll_direction = ScrollInstruction.SCROLL_LEFT
        else:
            self.scroll_direction = ScrollInstruction.SCROLL_UP
    
    def restart(self):
        self.current_row = 0;
        self.last_scroll_time = time.time();

    def bump(self, surface):
        self.last_scroll_time = 0
        if surface:
            self.refresh(surface)

    def refresh(self, surface):
        try:
            scroll = False
            header_row = self.table_fetcher.fetch_header_row();

            previous_row = self.current_row

            # Work out how many data rows we want
            if header_row is None:
                data_rows_to_fetch = self.num_rows_on_screen;
            else:
                data_rows_to_fetch = self.num_rows_on_screen - 1;

            # Scroll to the next page of results if necessary
            if self.scroll_interval > 0 and self.last_scroll_time + self.scroll_interval <= time.time():
                self.last_scroll_time = time.time();
                self.current_row += data_rows_to_fetch;

            # Fetch the rows, going back to the beginning if we've fallen
            # off the end
            table_rows = self.table_fetcher.fetch_data_rows(self.current_row, data_rows_to_fetch);
            if not table_rows:
                self.current_row = 0;
                table_rows = self.table_fetcher.fetch_data_rows(self.current_row, data_rows_to_fetch);

            if self.current_row != previous_row:
                scroll = True

            try:
                header_row = self.table_fetcher.fetch_header_row_for_page(start_row=self.current_row, page_length=data_rows_to_fetch);
            except AttributeError:
                header_row = self.table_fetcher.fetch_header_row();

            row_height_px = surface.get_height() / self.num_rows_on_screen;

            font = get_sensible_font(self.default_font_name, row_height_px);

            # Draw the header row if necessary
            pos_y = 0;
            if header_row:
                header_row.draw(surface, font, pos_y, row_height_px);
                pos_y += row_height_px;

            # Draw the table rows
            if table_rows:
                for row in table_rows:
                    row.draw(surface, font, pos_y, row_height_px);
                    pos_y += row_height_px;

            if scroll:
                if header_row:
                    return ScrollInstruction(pygame.Rect(0, row_height_px, surface.get_width(), surface.get_height() - row_height_px), self.scroll_direction)
                else:
                    return ScrollInstruction(surface.get_rect(), self.scroll_direction)
            else:
                return None
        except countdowntourney.TourneyException as e:
            traceback.print_exc();
            surface.fill((255, 0, 0, 255));
        except sqlite3.Error as e:
            traceback.print_exc();
            surface.fill((255, 128, 0, 255));
        return None

class TableIndexWidget(Widget):
    def __init__(self, fetcher, num_lines=12, num_columns=3, scroll_interval=10, font_name="sans-serif"):
        self.scroll_interval = scroll_interval
        self.preferred_lines_per_page = num_lines
        self.preferred_num_columns = num_columns
        self.current_page = 0
        self.last_scroll_time = time.time()
        self.font_name = font_name
        self.fetcher = fetcher

    def restart(self):
        self.last_scroll_time = time.time()
        self.current_page = 0

    def bump(self, surface):
        self.last_scroll_time = 0
        if surface:
            self.refresh(surface)

    def refresh(self, surface):
        scrolled = False
        assignments = self.fetcher.fetch_index()

        # If the preferred number of lines and columns would mean the last
        # page has less than half a column on it, extend the column size so
        # we can do it in one fewer page.
        names_per_page = self.preferred_num_columns * self.preferred_lines_per_page
        num_pages = (len(assignments) + names_per_page - 1) / names_per_page

        names_on_last_page = len(assignments) % names_per_page
        if names_on_last_page > 0 and names_on_last_page < self.preferred_lines_per_page / 2:
            num_pages -= 1
            num_columns = self.preferred_num_columns
            names_per_page = (len(assignments) + num_pages - 1) / num_pages
            lines_per_page = (names_per_page + num_columns - 1) / num_columns
            names_per_page = num_columns * lines_per_page
        else:
            lines_per_page = self.preferred_lines_per_page
            num_columns = self.preferred_num_columns

        names_per_page = num_columns * lines_per_page

        # Work out the line heights
        line_height = int(surface.get_height() / (lines_per_page + 1.5))
        title_height = int(line_height * 1.5)
        table_start_y = title_height

        previous_page = self.current_page

        # Is it time to scroll?
        if self.last_scroll_time + self.scroll_interval <= time.time():
            self.current_page += 1;
            self.last_scroll_time = time.time();

        if self.current_page * names_per_page >= len(assignments):
            self.current_page = 0;

        if previous_page != self.current_page:
            scrolled = True

        if len(assignments) == 0:
            return None

        line_padding = line_height / 5
        if line_padding < 2:
            line_padding = 2
        col_padding = (surface.get_width() / num_columns) / 5
        if col_padding < 10:
            col_padding = 10

        col_width = (surface.get_width() - (num_columns - 1) * col_padding) / num_columns

        table_width = col_width / 5
        if table_width < line_height:
            table_width = line_height
        name_width = col_width - table_width
        if name_width < 10:
            name_width = 10

        name_padding = line_height / 4

        if line_height <= line_padding or name_width >= col_width:
            # Screw this
            return None

        # Draw the title
        text = "Table Numbers - " + self.fetcher.get_round_name()
        font = get_sensible_font(self.font_name, int(line_height * 1.25) - line_padding)
        caption = make_text_label(font, text, teleostcolours.get("table_index_title_fg"), int(surface.get_width() * 4 / 5))
        surface.blit(caption, (0, 0))
        
        # Draw the page number
        if num_pages > 1:
            text = "page %d of %d" % (self.current_page + 1, num_pages)
            font = get_sensible_font(self.font_name, line_height - line_padding)
            caption = make_text_label(font, text, teleostcolours.get("table_index_page_number"), int(surface.get_width() / 5))
            surface.blit(caption, (surface.get_width() - caption.get_width(), int(line_height / 8)))

        x = 0
        font = get_sensible_font(self.font_name, line_height - line_padding)
        for col in range(num_columns):
            for line_no in range(lines_per_page):
                assignment_index = self.current_page * names_per_page + col * lines_per_page + line_no
                if assignment_index >= len(assignments):
                    break

                (name, table_list) = assignments[assignment_index]
                y = table_start_y + line_no * line_height + line_padding / 2

                name_label = pygame.Surface((name_width, line_height - line_padding), pygame.SRCALPHA)
                name_label.fill(teleostcolours.get("table_index_name_bg"))
                caption = make_text_label(font, name, teleostcolours.get("table_index_name_fg"), name_width - name_padding)
                name_label.blit(caption, (name_padding / 2, 0))

                table_label = pygame.Surface((table_width, line_height - line_padding), pygame.SRCALPHA)
                table_label.fill(teleostcolours.get("table_index_table_bg"))
                caption = make_text_label(font, table_list, teleostcolours.get("table_index_table_fg"), table_width)
                table_label.blit(caption, ((table_label.get_width() - caption.get_width()) / 2, 0))

                surface.blit(name_label, (x, y))
                surface.blit(table_label, (x + name_width, y))
            x += col_width + col_padding

        if scrolled:
            return ScrollInstruction(pygame.Rect(0, table_start_y, surface.get_width(), surface.get_height() - table_start_y))
        else:
            return None


class PagedFixturesWidget(Widget):
    def __init__(self, fetcher, num_lines=9, scroll_interval=10, font_name="sans-serif"):
        self.scroll_interval = scroll_interval;
        self.lines_per_page = num_lines;
        self.current_page = 0;
        self.last_scroll_time = time.time();
        self.font_name = font_name;
        self.fetcher = fetcher;
    
    def restart(self):
        self.last_scroll_time = time.time();
        self.current_page = 0;
 
    def bump(self, surface):
        self.last_scroll_time = 0
        if surface:
            self.refresh(surface)

    def refresh(self, surface):
        try:
            return self.refresh_aux(surface);
        except countdowntourney.TourneyException as e:
            traceback.print_exc();
            surface.fill((255, 0, 0, 255));
        except sqlite3.Error as e:
            traceback.print_exc();
            surface.fill((255, 128, 0, 255));
    
    def refresh_aux(self, surface):
        # The fetcher should fetch the games for the current round
        games = self.fetcher.fetch_games()
        pages = [];

        scrolled = False

        # Divide these games up into pages, putting no more than num_lines
        # games onto the screen. Don't split a clump of games on the same
        # table across multiple pages if we can avoid it. Also, a new
        # division always starts on a new page.
        page = [];
        games = sorted(games, key=lambda x : (x.round_no, x.division, x.table_no));
        prev_round_no = None;
        prev_division = None

        num_divisions = 0
        div_numbers = set()
        for g in games:
            if g.division not in div_numbers:
                num_divisions += 1
            div_numbers.add(g.division)

        # The page always starts with the round title, and any other rounds
        # on the same page have a title. This title takes up one line on the
        # page, so take that into account when deciding whether we can fit
        # a set of games on this page.

        num_titles = 1;
        while games:
            round_no = games[0].round_no;
            table_no = games[0].table_no;
            division = games[0].division;

            # How many games on this table?
            table_games = filter(lambda x : x.round_no == round_no and x.table_no == table_no, games);
            
            # Is this a different round or division from what we've already got
            # on the page? If so, and if we can't also fit all the games from
            # this round on the same page, start a new page
            if ((prev_round_no is not None and prev_round_no != round_no) or (prev_division is not None and prev_division != division)) and len(page) > 0:
                # How many games have we got in this round and division?
                num_games_this_round_div = len(filter(lambda x : x.round_no == round_no and x.division == division, games));
                if len(page) + num_titles + 1 + num_games_this_round_div > self.lines_per_page:
                    # New page
                    pages.append(page[:]);
                    page = [];
                else:
                    # Put this round's games on this page
                    num_titles += 1;
            # Will they fit on the page? If not, get a new page
            elif len(page) + len(table_games) + num_titles > self.lines_per_page:
                if len(page) > 0:
                    pages.append(page[:]);
                    page = [];

            # If they still won't fit on a page, fit as many as we can
            if len(page) + len(table_games) > self.lines_per_page:
                games_to_take = table_games[0:self.lines_per_page];
            else:
                games_to_take = table_games[:];

            for g in games_to_take:
                page.append(g);

            games = games[len(games_to_take):];
            prev_round_no = round_no;
            prev_division = division
        if page:
            pages.append(page[:]);

        if len(pages) == 0:
            return None;

        previous_page = self.current_page
        # Is it time to scroll?
        if self.last_scroll_time + self.scroll_interval <= time.time():
            self.current_page += 1;
            self.last_scroll_time = time.time();

        if self.current_page >= len(pages):
            self.current_page = 0;

        if self.current_page != previous_page:
            scrolled = True

        page = pages[self.current_page];

        # Work out some arcane constants
        top_padding_height = int(0.02 * surface.get_height());
        line_height = int((surface.get_height() - top_padding_height) / self.lines_per_page);
        fixtures_y = top_padding_height;

        round_name_left = 3 * line_height;

        table_y_pos = fixtures_y;
        table_index = -1;
        fixtures_x = 3 * line_height;
        fixtures_width = surface.get_width() - fixtures_x;
        name1_width_px = int(0.39 * fixtures_width);
        name1_x = fixtures_x;
        score_width_px = int(0.2 * fixtures_width);
        score_x = fixtures_x + int(0.4 * fixtures_width);
        name2_width_px = name1_width_px;
        name2_x = fixtures_x + int(0.61 * fixtures_width);

        round_name_colour = teleostcolours.get("fixtures_round_name")
        name1_colour = name2_colour = teleostcolours.get("fixtures_player_name")
        unknown_name1_colour = unknown_name2_colour = teleostcolours.get("fixtures_unknown_player_name")
        score_colour = teleostcolours.get("fixtures_score");

        # Make the red and green gradient shaded rectangles for the
        # left and right side of the fixture list
        shade_spacing = int(0.1 * line_height);
        red_left_shade = pygame.Surface((name1_width_px, line_height), pygame.SRCALPHA);
        red_right_shade = pygame.Surface((name2_width_px, line_height), pygame.SRCALPHA);
        green_left_shade = pygame.Surface((name1_width_px, line_height), pygame.SRCALPHA);
        green_right_shade = pygame.Surface((name2_width_px, line_height), pygame.SRCALPHA);
        yellow_left_shade = pygame.Surface((name1_width_px, line_height), pygame.SRCALPHA);
        yellow_right_shade = pygame.Surface((name2_width_px, line_height), pygame.SRCALPHA);
        green = teleostcolours.get("fixtures_winner_bg")
        green_transparent = teleostcolours.get("fixtures_winner_bg_transparent")
        red = teleostcolours.get("fixtures_loser_bg")
        red_transparent = teleostcolours.get("fixtures_loser_bg_transparent")
        yellow = teleostcolours.get("fixtures_draw_bg")
        yellow_transparent = teleostcolours.get("fixtures_draw_bg_transparent")

        shade_area_horiz_gradient(red_left_shade, red_left_shade.get_rect(), red, red_transparent);
        shade_area_horiz_gradient(red_right_shade, red_right_shade.get_rect(), red_transparent, red);
        shade_area_horiz_gradient(green_left_shade, green_left_shade.get_rect(), green, green_transparent);
        shade_area_horiz_gradient(green_right_shade, green_right_shade.get_rect(), green_transparent, green);
        shade_area_horiz_gradient(yellow_left_shade, yellow_left_shade.get_rect(), yellow, yellow_transparent)
        shade_area_horiz_gradient(yellow_right_shade, yellow_right_shade.get_rect(), yellow_transparent, yellow)

        #font = get_sensible_font(self.font_name, title_height);
        #heading = font.render(round_name, 1, (255, 255, 255));
        #surface.blit(heading, (title_left, title_top));

        # Divide the games in "page" into tables
        tables = [];
        prev_table_no = None;
        prev_division = None;
        prev_round_no = None;
        table = [];
        for g in page:
            if g is None or (prev_table_no is not None and prev_table_no != g.table_no) or (prev_round_no is not None and prev_round_no != g.round_no) or (prev_division is not None and prev_division != g.division):
                tables.append(table[:]);
                table = [];
            if g is not None:
                table.append(g);
                prev_table_no = g.table_no;
                prev_round_no = g.round_no;
                prev_division = g.division
        if table:
            tables.append(table[:]);

        # Draw the tables
        prev_round_no = None;
        prev_division = None;
        for t in tables:
            if prev_round_no != t[0].round_no or prev_division != t[0].division:
                # New round, so print the round name
                font = get_sensible_font(self.font_name, int(0.8 * line_height));
                round_name = self.fetcher.get_round_name(t[0].round_no);
                if num_divisions > 1:
                    round_name += "   " + self.fetcher.get_division_name(t[0].division)
                round_name_label = make_text_label(font, round_name, round_name_colour)
                surface.blit(round_name_label, (round_name_left, int(table_y_pos + 0.2 * line_height)));
                table_y_pos += line_height;

            table_index += 1;

            shade_colour = teleostcolours.get("fixtures_table_bg")

            inter_table_padding = int(0.1 * line_height * len(t));
            table_number_padding = inter_table_padding;

            shade_area(surface, (fixtures_x, table_y_pos + inter_table_padding / 2, surface.get_width(), line_height * len(t) - inter_table_padding), shade_colour);

            # Draw the table number
            table_number_height = line_height * len(t) - table_number_padding;
            table_number_width = 3 * line_height - table_number_padding;
            modified_line_height = (len(t) * line_height - inter_table_padding) / len(t);
            
            table_number_label = pygame.Surface((table_number_width, table_number_height), pygame.SRCALPHA);
            table_number_label.fill(teleostcolours.get("fixtures_table_number_bg"))
            
            font = get_sensible_font(self.font_name, min(table_number_height, table_number_width));
            caption = make_text_label(font, str(t[0].table_no), teleostcolours.get("fixtures_table_number_fg"))

            top = (table_number_label.get_height() - caption.get_height()) / 2;
            if top < 0:
                top = 0;
            left = (table_number_label.get_width() - caption.get_width()) / 2;
            if left < 0:
                left = 0;

            table_number_label.blit(caption, (left, top));

            surface.blit(table_number_label, (table_number_padding / 2, int(table_y_pos + table_number_padding / 2)));

            # Write each fixture on this table
            font = get_sensible_font(self.font_name, modified_line_height);

            y_pos = int(table_y_pos + inter_table_padding / 2);
            if os.name == "nt":
                text_y_pos = int(y_pos + line_height * 0.2);
            else:
                text_y_pos = y_pos;

            for g in t:
                x_pos = fixtures_x;
                names = (str(g.p1), str(g.p2))
                
                team1 = g.p1.get_team()
                if team1:
                    team1 = team1.get_colour_tuple()
                team2 = g.p2.get_team()
                if team2:
                    team2 = team2.get_colour_tuple()

                name1_label = make_text_label(font, names[0], name1_colour if g.p1.is_player_known() else unknown_name1_colour)

                if team1:
                    this_name1_width_px = int(0.9 * name1_width_px)
                    team1_label = make_team_dot(int(0.1 * name1_width_px), modified_line_height, team1)
                else:
                    team1_label = None
                    this_name1_width_px = name1_width_px

                name1_label = make_text_label(font, names[0], name1_colour if g.p1.is_player_known() else unknown_name1_colour, this_name1_width_px)
                if team2:
                    this_name2_width_px = int(0.9 * name2_width_px)
                    this_name2_x = name2_x + int(0.1 * name2_width_px)
                    team2_label = make_team_dot(int(0.1 * name2_width_px), modified_line_height, team2)
                else:
                    this_name2_width_px = name2_width_px
                    this_name2_x = name2_x
                    team2_label = None
                name2_label = make_text_label(font, names[1], name2_colour if g.p2.is_player_known() else unknown_name2_colour, this_name2_width_px)

                if g.is_complete():
                    score_str = g.format_score();
                else:
                    score_str = "v";

                score_label = make_text_label(font, score_str, score_colour, score_width_px)

                if g.is_complete():
                    gap = int(0.1 * modified_line_height);
                    if g.s1 > g.s2:
                        left_shade = green_left_shade
                        right_shade = red_right_shade
                    elif g.s2 > g.s1:
                        left_shade = red_left_shade
                        right_shade = green_right_shade
                    else:
                        left_shade = yellow_left_shade
                        right_shade = yellow_right_shade
                    surface_merge(surface, left_shade, (name1_x + shade_spacing, y_pos + shade_spacing), (0, 0, name1_width_px - shade_spacing, modified_line_height - 2 * shade_spacing))
                    surface_merge(surface, right_shade, (name2_x - shade_spacing, y_pos + shade_spacing), (0, 0, name2_width_px - shade_spacing, modified_line_height - 2 * shade_spacing))


                surface.blit(name1_label, (name1_x + this_name1_width_px - name1_label.get_width(), text_y_pos));
                if team1_label:
                    surface.blit(team1_label, ((name1_x + this_name1_width_px), y_pos))
                surface.blit(score_label, (score_x + (score_width_px - score_label.get_width()) / 2, text_y_pos));
                surface.blit(name2_label, (this_name2_x, text_y_pos));
                if team2_label:
                    surface.blit(team2_label, (name2_x, y_pos))
                y_pos += modified_line_height;
                text_y_pos += modified_line_height;

            # The next table should be drawn at len(t) full line heights from
            # the top of this table. This will also take account of the
            # inter-table vertical padding.
            table_y_pos += line_height * len(t);
            prev_round_no = t[0].round_no;
            prev_division = t[0].division

        if scrolled:
            return ScrollInstruction(pygame.Rect(0, 0, surface.get_width(), surface.get_height()))
        else:
            return None

class LabelWidget(Widget):
    def __init__(self, text, left_pc, top_pc, width_pc, height_pc, text_colour_name=None, bg_colour_name=None, font_name="sans-serif"):
        self.text = text;
        self.text_colour_name = text_colour_name;
        self.bg_colour_name = bg_colour_name;
        self.font_name = font_name;
        self.left_pc = left_pc;
        self.top_pc = top_pc;
        self.width_pc = width_pc;
        self.height_pc = height_pc;

    def refresh(self, surface):
        if self.width_pc is None:
            # If width part of rect is None, we can use as much horizontal
            # space as we need.
            width = surface.get_width();
        else:
            width = surface.get_width() * self.width_pc / 100;
        height = surface.get_height() * self.height_pc / 100;

        font = get_sensible_font(self.font_name, height);

        top_px = surface.get_height() * self.top_pc / 100;
        left_px = surface.get_width() * self.left_pc / 100;

        self.text_colour = teleostcolours.get(self.text_colour_name)

        if self.bg_colour_name:
            self.bg_colour = teleostcolours.get(self.bg_colour_name)
        else:
            self.bg_colour = None

        label = pygame.Surface((width, height), flags=pygame.SRCALPHA);
        caption = make_text_label(font, self.text, self.text_colour, width)

        if self.bg_colour:
            label.fill(self.bg_colour);

        label.blit(caption, (0,0));
        surface.blit(label, (left_px, top_px));
        return None


class ShadedArea(Widget):
    def __init__(self, colour=(0,0,0,128), colour_name=None):
        if colour:
            if len(colour) < 4:
                self.colour = (colour[0], colour[1], colour[2], 128)
            else:
                self.colour = colour
            self.colour_name = None
        else:
            self.colour_name = colour_name
    
    def refresh(self, surface):
        shaded = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA);
        if self.colour_name:
            self.colour = teleostcolours.get(self.colour_name)
        shaded.fill(self.colour);
        surface.blit(shaded, (0, 0));

###############################################################################

class TestStandingsFetcher(object):
    def __init__(self):
        self.data = [
                [ 1, "Jack Hurst", 6, 5, 414 ],
                [ 2, "Giles Hutchings", 6, 5, 401 ],
                [ 3, "Jack Worsley", 6, 5, 400 ],
                [ 4, "Jonathan Rawlinson", 6, 5, 382 ],
                [ 5, "Innis Carson", 6, 5, 380 ],
                [ 6, "Mark Deeks", 6, 5, 376 ],
                [ 7, "Adam Gillard", 6, 5, 372 ],
                [ 8, "Conor Travers", 6, 4, 415 ],
                [ 9, "Jen Steadman", 6, 4, 375 ],
                [ 10, "Matt Bayfield", 6, 4, 372 ],
                [ 10, "David Barnard", 6, 4, 372 ],
                [ 12, "James Robinson", 6, 4, 368 ]
        ];
        
        self.rows = [];
        for data_row in self.data:
            row = TableRow();
            row.append_value(RowValue(str(data_row[0]), PercentLength(15), alignment=ALIGN_RIGHT, text_colour=(255,255,0)));
            row.append_value(RowValue(str(data_row[1]), PercentLength(50)));
            row.append_value(RowValue(str(data_row[2]), PercentLength(10), alignment=ALIGN_RIGHT, text_colour=(0, 128, 128)));
            row.append_value(RowValue(str(data_row[3]), PercentLength(10), alignment=ALIGN_RIGHT, text_colour=(0, 255, 255)));
            row.append_value(RowValue(str(data_row[4]), PercentLength(15), alignment=ALIGN_RIGHT, text_colour=(0, 255, 255)));
            #row.set_border(bottom_border=LineStyle(pygame.Color(64,64,64), 1));
            self.rows.append(row);
    
    def fetch_header_row(self):
        row = TableRow();
        grey = (128, 128, 128);
        row.append_value(RowValue("Pos", PercentLength(15), alignment=ALIGN_RIGHT, text_colour=grey));
        row.append_value(RowValue("Name", PercentLength(50), text_colour=grey));
        row.append_value(RowValue("P", PercentLength(10), alignment=ALIGN_RIGHT, text_colour=grey));
        row.append_value(RowValue("W", PercentLength(10), alignment=ALIGN_RIGHT, text_colour=grey));
        row.append_value(RowValue("Pts", PercentLength(15), alignment=ALIGN_RIGHT, text_colour=grey));
        row.set_border(bottom_border=LineStyle(pygame.Color(128, 128, 128), 1));
        return row;
    
    def fetch_data_rows(self, start_row, num_rows):
        if start_row >= len(self.rows):
            return None;
        else:
            return self.rows[start_row:(start_row + num_rows)];

if __name__ == "__main__":
    pygame.init();

    table_fetcher = TestStandingsFetcher();
    fontfilename = "/usr/share/fonts/truetype/futura/Futura Condensed Bold.ttf";

    view = View();
    view.add_view(TableWidget(table_fetcher, 5, scroll_interval=1), top_pc=0, height_pc=50, left_pc=0, width_pc=100);
    view.add_view(TableWidget(table_fetcher, 10, scroll_interval=2), top_pc=50, height_pc=50, left_pc=0, width_pc=50);
    view.add_view(TableWidget(table_fetcher, 10, scroll_interval=3), top_pc=50, height_pc=50, left_pc=50, width_pc=50);

    screen_width = 1024;
    screen_height = 600;
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE);

    for i in range(0, 7):
        screen.fill((0, 0, 32, 255));
        view.refresh(screen);
        pygame.display.flip();
        time.sleep(2);

    sys.exit(0);
