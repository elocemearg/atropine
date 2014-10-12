#!/usr/bin/env python

import time;
import curses;
import sys;
import argparse;
import pickle;
import socket;
import threading;
import re;
import string;
import pygame;
import errno;
import os;

# For the server, the list of client sockets connected to us
connected_sockets = [];
connected_sockets_lock = threading.Lock();

ALIGN_LEFT = 0
ALIGN_CENTRE = 1
ALIGN_RIGHT = 2

default_font_name = "sans-serif";

# Functions to get the colour pair number given bg and fg colours
def colour2(fg, bg):
	return curses.color_pair(bg * 8 + fg);

def colour(fg):
	return curses.color_pair(fg);

def recvall(sock, length):
	message = "";
	while length > 0:
		to_recv = min(4096, length);
		chunk = sock.recv(to_recv);
		length -= len(chunk);
		message = message + chunk;
	return message;

class PercentageWidth(object):
	def __init__(self, pc):
		self.pc = pc;
	
	def get_px(self, surface):
		return int(surface.get_width() * self.pc / 100);

class PercentageHeight(object):
	def __init__(self, pc):
		self.pc = pc;
	
	def get_px(self, surface):
		return int(surface.get_height() * self.pc / 100);

def limit_label_width(label, max_width):
	if label.get_width() <= max_width:
		return label;
	try:
		return pygame.transform.smoothscale(label, (max_width, label.get_height()));
	except:
		return pygame.transform.scale(label, (max_width, label.get_height()));

def get_sensible_font(font_name, desired_line_size, sysfont=True):
	low = 10;
	high = 200;
	while True:
		size = (low + high) / 2;
		if sysfont:
			font = pygame.font.SysFont(font_name, size);
		else:
			font = pygame.font.Font(font_name, size);
		if font.get_linesize() == desired_line_size:
			break;
		elif font.get_linesize() < desired_line_size:
			low = size + 1;
		else:
			high = size - 1;
		if low > high:
			size = high;
			break;
	if sysfont:
		font = pygame.font.SysFont(font_name, size);
	else:
		font = pygame.font.Font(font_name, size);
	return font;


def draw_label(surface, rect, text, fgcolour=(255,255,255), bgcolour=None, align=ALIGN_LEFT, border_colour=None, border_size=None):
	(left, top, width, height) = rect;

	if width <= 0 or height <= 0:
		return;

	if font_file:
		font = get_sensible_font(font_file, height, sysfont=False);
	else:
		font = get_sensible_font(default_font_name, height, sysfont=True);

	xspacing = int(font.get_linesize() * 0.1);

	caption = font.render(text, 1, fgcolour);
	if width is None:
		width = caption.get_width();
	label = pygame.Surface((width, height), pygame.SRCALPHA);
	if bgcolour:
		label.fill(bgcolour);
	else:
		label.blit(surface, (0,0), area=(left, top, width, height));
	
	caption = limit_label_width(caption, width - 2 * xspacing);

	if align == ALIGN_LEFT:
		label.blit(caption, (xspacing, 0));
	elif align == ALIGN_RIGHT:
		x = width - (caption.get_width() + xspacing);
		label.blit(caption, (x, 0));
	else:
		x = (width - caption.get_width()) / 2;
		label.blit(caption, (x, 0));
	
	if border_size:
		surface.fill(border_colour,
				(left - border_size, top - border_size,
					width + 2 * border_size, height + 2 * border_size));
	
	surface.blit(label, (left, top));

def shade_area(surface, rect, colour):
	tmp = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA);
	tmp.blit(surface, (0, 0), rect);
	shade = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA);
	shade.fill(colour);
	tmp.blit(shade, (0, 0));
	surface.blit(tmp, (rect[0], rect[1]));

def draw_flippything(surface, rect, letter_width, letter_height, border_px, border_colour, spacing, state, text, unrevealed_text):
	surface.fill(border_colour, (rect[0] - border_px, rect[1] - border_px, rect[2] + 2 * border_px, rect[3] + 2 * border_px));
	if state == 0:
		draw_label(surface, rect, unrevealed_text, fgcolour=(128, 128, 128), bgcolour=(0, 0, 255), align=ALIGN_CENTRE);
	elif state == 1:
		x = rect[0];
		y = rect[1];
		x_step = letter_width + spacing;
		for l in list(text):
			if l and l != ' ':
				draw_label(surface, (x, y, letter_width, letter_height), l, fgcolour=(255, 255, 255), bgcolour=(0, 0, 255), align=ALIGN_CENTRE);
			x += x_step;
	else:
		draw_label(surface, rect, "INCORRECT", fgcolour=(255, 255, 255), bgcolour=(0, 0, 255), align=ALIGN_CENTRE);


class GameState:
	def __init__(self):
		self.title = "";
		self.p1 = "";
		self.p2 = "";
		self.s1 = 0;
		self.s2 = 0;
		self.numbers_rack = (0, 0, 0, 0, 0, 0);
		self.numbers_target = 0;
		self.letters_rack = "";
		self.bottom_rack = "";
		self.conundrum_scramble = "";
		self.conundrum_top_state = 0;
		self.conundrum_solution = "";
		self.conundrum_bottom_state = 0;
		self.round_type = "";
	
	def load(self, filename):
		f = open(filename, "rb");
		pickled_state = f.read();
		state = pickle.loads(pickled_state);
		self.set_state(state);
	
	def save(self, filename):
		f = open(filename, "wb");
		pickled_state = pickle.dumps(state);
		f.write(pickled_state);
		f.close();

	def reveal_conundrum_scramble(self):
		if self.conundrum_top_state == 0:
			self.conundrum_top_state = 1;
		else:
			self.conundrum_top_state = 0;
	
	def reveal_conundrum_incorrect(self):
		if self.conundrum_bottom_state == 2:
			self.conundrum_bottom_state = 0;
		else:
			self.conundrum_bottom_state = 2;

	def reveal_conundrum_answer(self):
		if self.conundrum_top_state == 0:
			return;
		if self.conundrum_bottom_state == 1:
			self.conundrum_bottom_state = 0;
		else:
			self.conundrum_bottom_state = 1;

	def read_message(self, sock, tout=None):
		c = "";
		len_str = "";
		while c != '\n':
			try:
				if c == "":
					sock.settimeout(tout);
				else:
					sock.settimeout(0);
				c = sock.recv(1);
			except socket.timeout, e:
				return -1;
			except socket.error, e:
				(errnum, errstr) = e;
				if errnum == errno.EINTR:
					continue;
				else:
					raise;
			if c == 'A':
				return 1;
			elif c == 'B':
				return 2;
			elif c == 'C':
				return 3;
			elif c != '\n':
				len_str = len_str + c;
		message_length = int(len_str);
		message = None;
		while message == None:
			try:
				message = recvall(sock, message_length);
			except socket.error, e:
				(errnum, errstr) = e;
				if errnum == errno.EINTR:
					continue;
				else:
					raise;
		state = pickle.loads(message);
		self.set_state(state);
		return 0;

	def set_state(self, state):
		self.title = state.title;
		self.p1 = state.p1;
		self.p2 = state.p2;
		self.s1 = state.s1;
		self.s2 = state.s2;
		self.numbers_rack = state.numbers_rack;
		self.letters_rack = state.letters_rack;
		self.bottom_rack = state.bottom_rack;
		self.numbers_target = state.numbers_target;
		self.conundrum_scramble = state.conundrum_scramble;
		self.conundrum_solution = state.conundrum_solution;
		self.conundrum_top_state = state.conundrum_top_state;
		self.conundrum_bottom_state = state.conundrum_bottom_state;
		self.round_type = state.round_type;

def draw_rectangle(win, tly, tlx, bry, brx):
	win.addch(tly, tlx, curses.ACS_ULCORNER);
	win.addch(tly, brx, curses.ACS_URCORNER);
	win.addch(bry, tlx, curses.ACS_LLCORNER);
	win.addch(bry, brx, curses.ACS_LRCORNER);
	for x in xrange(tlx + 1, brx):
		win.addch(tly, x, curses.ACS_HLINE);
		win.addch(bry, x, curses.ACS_HLINE);
	for y in xrange(tly + 1, bry):
		win.addch(y, tlx, curses.ACS_VLINE);
		win.addch(y, brx, curses.ACS_VLINE);

class GUILiveGameWindow:
	title_height = PercentageHeight(8);
	nameplate_top = PercentageHeight(12);
	nameplate_height = PercentageHeight(6);
	nameplate1_left = PercentageWidth(5);
	nameplate2_left = PercentageWidth(55);
	nameplate1_width = PercentageWidth(40);
	nameplate2_width = PercentageWidth(40);
	nameplate_border = PercentageHeight(0.5);
	score_border = PercentageHeight(0.5);

	score_top = PercentageHeight(20);
	score_height = PercentageHeight(20);
	score1_left = PercentageWidth(12.5);
	score2_left = PercentageWidth(62.5);
	score1_width = PercentageWidth(25);
	score2_width = PercentageWidth(25);

	letters_top = PercentageHeight(55);
	letters_max_width = PercentageWidth(90);
	letters_max_height = PercentageHeight(40);
	letter_ratio = 1; # width/height
	num_letters = 9;

	letters_border = PercentageWidth(2);
	letters_spacing = PercentageWidth(1);

	numbers_top = PercentageHeight(50);
	numbers_left = PercentageWidth(10);
	numbers_width = PercentageWidth(80);

	target_top = PercentageHeight(53);
	target_left = PercentageWidth(35);
	target_width = PercentageWidth(30);
	target_height = PercentageHeight(19);

	numbers_sel_top = PercentageHeight(75);
	numbers_sel_max_height = PercentageHeight(23);
	numbers_sel_max_width = PercentageWidth(90);
	numbers_sel_border = PercentageWidth(1);
	numbers_sel_spacing = PercentageWidth(1);
	number_ratio = 1;
	num_numbers = 6;

	con_top = letters_top;
	con_max_width = letters_max_width;
	con_max_height = letters_max_height;
	con_border = letters_border;
	con_spacing = letters_spacing;

	def __init__(self, background_surface=None):
		self.background = background_surface;
		self.background_scaled = None;

	def rescale_background(self, surface):
		x_scale = float(surface.get_width()) / float(self.background.get_width());
		y_scale = float(surface.get_height()) / float(self.background.get_height());
		scale = max((x_scale, y_scale));
		scaled_width = int(scale * self.background.get_width());
		scaled_height = int(scale * self.background.get_height());
		self.background_scaled = pygame.transform.scale(self.background, (scaled_width, scaled_height));
	
	def draw(self, surface, state):
		if self.background:
			if self.background_scaled is None:
				self.rescale_background(surface);
			bg_scaled_top = (self.background_scaled.get_height() - surface.get_height()) / 2;
			bg_scaled_left = (self.background_scaled.get_width() - surface.get_width()) / 2;
			surface.blit(self.background_scaled, (0, 0), area=(bg_scaled_left, bg_scaled_top, bg_scaled_left + surface.get_width(), bg_scaled_top + surface.get_height()));
		else:
			surface.fill((0, 0, 0, 255));

		title_colour = (255, 255, 255);
		name_colour = (255, 255, 255);
		name_bg = (0, 0, 192);
		score_colour = (255, 255, 255);
		score_bg = (0, 0, 255);
		letter_colour = (255, 255, 255);
		letter_bg = (0, 0, 192);
		target_colour = (255, 255, 255);
		target_bg = (0, 0, 255);
		number_colour = (255, 255, 255);
		number_bg = (0, 0, 192);

		# Draw title
		draw_label(surface, (0, 0, surface.get_width(), self.title_height.get_px(surface)), state.title, fgcolour=title_colour, align=ALIGN_CENTRE);

		# Draw shaded area
		score_border = int(self.nameplate_height.get_px(surface) / 2);
		backing_height = self.score_top.get_px(surface) + self.score_height.get_px(surface) - self.nameplate_top.get_px(surface) + score_border * 2;
		shade_area(surface,
				(self.nameplate1_left.get_px(surface) - score_border,
					self.nameplate_top.get_px(surface) - score_border,
					self.nameplate1_width.get_px(surface) + score_border * 2,
					backing_height),
				(0, 0, 0, 96)
		);
		shade_area(surface,
				(self.nameplate2_left.get_px(surface) - score_border,
					self.nameplate_top.get_px(surface) - score_border,
					self.nameplate2_width.get_px(surface) + score_border * 2,
					backing_height),
				(0, 0, 0, 96)
		);

		# Draw nameplates
		draw_label(surface,
				(self.nameplate1_left.get_px(surface),
					self.nameplate_top.get_px(surface),
					self.nameplate1_width.get_px(surface),
					self.nameplate_height.get_px(surface)),
				state.p1, fgcolour=name_colour,
				bgcolour=name_bg, align=ALIGN_CENTRE,
				border_colour=(192, 192, 192),
				border_size=self.nameplate_border.get_px(surface));
		draw_label(surface,
				(self.nameplate2_left.get_px(surface),
					self.nameplate_top.get_px(surface),
					self.nameplate2_width.get_px(surface),
					self.nameplate_height.get_px(surface)),
				state.p2, fgcolour=name_colour,
				bgcolour=name_bg, align=ALIGN_CENTRE,
				border_colour=(192, 192, 192),
				border_size=self.nameplate_border.get_px(surface));
	
		score1_left_px = self.score1_left.get_px(surface);
		score2_left_px = self.score2_left.get_px(surface);
		score1_width_px = self.score1_width.get_px(surface);
		score2_width_px = self.score2_width.get_px(surface);
		score_height_px = self.score_height.get_px(surface);

		if score_height_px * 2 < score1_width_px:
			score1_left_px += (score1_width_px - score_height_px * 2) / 2
			score1_width_px = score_height_px * 2
		if score_height_px * 2 < score2_width_px:
			score2_left_px += (score2_width_px - score_height_px * 2) / 2
			score2_width_px = score_height_px * 2

		# Draw scores
		draw_label(surface,
				(score1_left_px,
					self.score_top.get_px(surface),
					score1_width_px, score_height_px),
				str(state.s1), fgcolour=score_colour,
				bgcolour=score_bg, align=ALIGN_RIGHT,
				border_colour=(192, 192, 192),
				border_size=self.nameplate_border.get_px(surface));
		draw_label(surface,
				(score2_left_px,
					self.score_top.get_px(surface),
					score2_width_px, score_height_px),
				str(state.s2), fgcolour=score_colour,
				bgcolour=score_bg, align=ALIGN_RIGHT,
				border_colour=(192, 192, 192),
				border_size=self.nameplate_border.get_px(surface));

		# Shade area
		if state.round_type in ("L", "N", "C"):
			shade_area(surface, (
				0, surface.get_height() / 2,
				surface.get_width(),
				surface.get_height() / 2),
				(0, 0, 0, 96)
			);

		if state.round_type == 'L':
			letters_max_width_px = self.letters_max_width.get_px(surface);
			letters_max_height_px = self.letters_max_height.get_px(surface);
			letter_width_px = (letters_max_width_px - 2 * self.letters_border.get_px(surface) - (self.num_letters - 1) * self.letters_spacing.get_px(surface)) / 9;
			letter_height_px = (letters_max_height_px - 4 * self.letters_border.get_px(surface)) / 2;
			if letter_width_px > letter_height_px * self.letter_ratio:
				letter_width_px = letter_height_px * self.letter_ratio;
				letters_width_px = self.num_letters * letter_width_px + self.letters_border.get_px(surface) * 2 + (self.num_letters - 1) * self.letters_spacing.get_px(surface);
				letters_height_px = letters_max_height_px;
			elif letter_width_px < letter_height_px * self.letter_ratio:
				letter_height_px = int(letter_width_px / self.letter_ratio);
				letters_height_px = 2 * letter_height_px + 4 * self.letters_border.get_px(surface);
				letters_width_px = letters_max_width_px;
			else:
				letters_width_px = letters_max_width_px;
				letters_height_px = letters_max_height_px;
			letters_left_px = (surface.get_width() - letters_width_px) / 2;
			letters_top_px = self.letters_top.get_px(surface);

			letters_start_x = letters_left_px + self.letters_border.get_px(surface);
			letters_start_y = letters_top_px + self.letters_border.get_px(surface);

			letters_x = letters_start_x;
			letters_x_step = letter_width_px + self.letters_spacing.get_px(surface);

			letters_border_px = self.letters_border.get_px(surface);

			# Draw backing
			surface.fill((0, 192, 255), (letters_left_px, letters_top_px, letters_width_px, letters_height_px));

			# Remove from the top rack those letters in the bottom rack
			top_rack = list(state.letters_rack.upper());
			bottom_rack = list(state.bottom_rack.upper());

			for l in bottom_rack:
				for i in range(0, len(top_rack)):
					if top_rack[i] == l:
						top_rack[i] = ' ';
						break;

			#for l in top_rack:
			#	if l:
			#		draw_label(surface,
			#				(letters_x, letters_start_y,
			#					letter_width_px, letter_height_px),
			#				l, fgcolour=letter_colour,
			#				bgcolour=letter_bg, align=ALIGN_CENTRE);
			#	letters_x += letters_x_step;

			flippything_border_px = letters_border_px / 2;
			flippything_border_colour = (0, 0, 128);
			draw_flippything(surface, 
					(letters_start_x,
						letters_start_y,
						letters_width_px - 2 * letters_border_px,
						letter_height_px),
					letter_width_px, letter_height_px,
					flippything_border_px, flippything_border_colour,
					self.letters_spacing.get_px(surface),
					1, "".join(top_rack), "");

			draw_flippything(surface, 
					(letters_start_x,
						letters_start_y + letter_height_px + 2 * letters_border_px,
						letters_width_px - 2 * letters_border_px,
						letter_height_px),
					letter_width_px, letter_height_px,
					flippything_border_px, flippything_border_colour,
					self.letters_spacing.get_px(surface),
					1, "".join(bottom_rack), "");
		elif state.round_type == 'N':
			if state.numbers_target is None or state.numbers_target <= 0:
				target_str = "";
			else:
				target_str = str(state.numbers_target);

			# Draw backing for target
			target_border_px = self.target_height.get_px(surface) / 20;
			surface.fill((0, 192, 255),
					(self.target_left.get_px(surface) - target_border_px,
					self.target_top.get_px(surface) - target_border_px,
					self.target_width.get_px(surface) + 2 * target_border_px,
					self.target_height.get_px(surface) + 2 * target_border_px));

			# Draw numbers target
			draw_label(surface,
					(self.target_left.get_px(surface),
						self.target_top.get_px(surface),
						self.target_width.get_px(surface),
						self.target_height.get_px(surface)),
					target_str, fgcolour=target_colour,
					bgcolour=target_bg, align=ALIGN_CENTRE);

			numbers_sel_top_px = self.numbers_sel_top.get_px(surface);
			numbers_sel_width_px = self.numbers_sel_max_width.get_px(surface);
			numbers_sel_height_px = self.numbers_sel_max_height.get_px(surface);
			
			number_width = (numbers_sel_width_px - (self.num_numbers - 1) * self.numbers_sel_spacing.get_px(surface) - 2 * self.numbers_sel_border.get_px(surface)) / self.num_numbers;
			number_height = numbers_sel_height_px - 2 * self.numbers_sel_border.get_px(surface);
			if number_width > number_height * self.number_ratio:
				number_width = int(number_height * self.number_ratio);
				numbers_sel_width_px = self.num_numbers * number_width + (self.num_numbers - 1) * self.numbers_sel_spacing.get_px(surface) + 2 * self.numbers_sel_border.get_px(surface);
			elif number_width < number_height * self.number_ratio:
				number_height = int(number_width / self.number_ratio);
				numbers_sel_height_px = number_height + 2 * self.numbers_sel_border.get_px(surface);

			numbers_sel_left_px = (surface.get_width() - numbers_sel_width_px) / 2;
			numbers_sel_start_x = numbers_sel_left_px + self.numbers_sel_border.get_px(surface);
			numbers_sel_x_step = number_width + self.numbers_sel_spacing.get_px(surface);
			numbers_sel_x = numbers_sel_start_x;
			numbers_sel_y = numbers_sel_top_px + self.numbers_sel_border.get_px(surface);

			# Draw backing for numbers
			surface.fill((0, 192, 255),
					(numbers_sel_left_px, numbers_sel_top_px,
						numbers_sel_width_px, numbers_sel_height_px));

			# Draw numbers
			if state.numbers_rack:
				for n in state.numbers_rack:
					draw_label(surface,
							(numbers_sel_x, numbers_sel_y,
								number_width, number_height),
							str(n), fgcolour=number_colour,
							bgcolour=number_bg, align=ALIGN_CENTRE);
					numbers_sel_x += numbers_sel_x_step;
		elif state.round_type == 'C':
			con_top_px = self.con_top.get_px(surface);
			con_width_px = self.con_max_width.get_px(surface);
			con_height_px = self.con_max_height.get_px(surface);
			letter_width = (con_width_px - 2 * self.con_border.get_px(surface) - (self.num_letters - 1) * self.con_spacing.get_px(surface)) / self.num_letters;
			letter_height = (con_height_px - 4 * self.con_border.get_px(surface)) / 2;
			if letter_width > letter_height * self.letter_ratio:
				letter_width = int(letter_height * self.letter_ratio);
				con_width_px = self.num_letters * letter_width + (self.num_letters - 1) * self.con_spacing.get_px(surface) + 2 * self.con_border.get_px(surface);
			elif letter_width < letter_height * self.letter_ratio:
				letter_height = int(letter_width / self.letter_ratio);
				con_height_px = 2 * letter_height + 4 * self.con_border.get_px(surface);
			con_left_px = (surface.get_width() - con_width_px) / 2;
			con_border_px = self.con_border.get_px(surface);

			surface.fill((0, 192, 255), (con_left_px, con_top_px, con_width_px, con_height_px));

			flippything_border_px = int(con_border_px / 2);
			flippything_border_colour = (0, 0, 128);
			draw_flippything(surface, 
					(con_left_px + con_border_px,
						con_top_px + con_border_px,
						con_width_px - 2 * con_border_px, letter_height),
					letter_width, letter_height,
					flippything_border_px, flippything_border_colour,
					self.con_spacing.get_px(surface),
					state.conundrum_top_state,
					state.conundrum_scramble, "COUNTDOWN");

			draw_flippything(surface, 
					(con_left_px + con_border_px,
						con_top_px + letter_height + 3 * con_border_px,
						con_width_px - 2 * con_border_px, letter_height),
					letter_width, letter_height,
					flippything_border_px, flippything_border_colour,
					self.con_spacing.get_px(surface),
					state.conundrum_bottom_state,
					state.conundrum_solution, "CONUNDRUM");


class CursesLiveGameWindow:
	def set_window_size(self, win):
		self.win = win;
		self.win.scrollok(1);
		(self.height, self.width) = win.getmaxyx();

		self.ypad = 1;
		self.title_y = self.ypad;
		self.score_y = self.ypad + 2;
		self.letters_y = self.ypad + 6;
		self.number_target_y = self.ypad + 6;
		self.number_rack_y = self.ypad + 8;
		self.top_flippything_y = self.ypad + 6;
		self.bottom_flippything_y = self.ypad + 8;
		self.bottom_rack_y = self.ypad + 8;

	def __init__(self, win):
		self.set_window_size(win);
	
	def draw(self, state):
		self.win.erase();
		self.win.addstr(self.title_y, 0, ("{0:^" + str(self.width) + "}").format(state.title), curses.A_REVERSE);

		# Need four characters for the score, and the number of
		# characters in the longest name. e.g.
		#
		#              Alice Aardvark  30
		#              Bob Bravo       43

		player_name_attr = curses.A_BOLD;
		score_attr = colour(curses.COLOR_YELLOW) | curses.A_BOLD;

		max_name_length = self.width - 4;
		name_field_length = min(max_name_length, max(len(state.p1), len(state.p2)));
		score_width = 4 + name_field_length;
		self.win.move(self.score_y, (self.width - score_width) / 2);
		self.win.addstr(("{0:<" + str(name_field_length) + "." + str(name_field_length) + "}").format(state.p1), player_name_attr);
		self.win.addstr("{0:>4}".format(state.s1), score_attr);
		self.win.move(self.score_y + 1, (self.width - score_width) / 2);
		self.win.addstr(("{0:<" + str(name_field_length) + "." + str(name_field_length) + "}").format(state.p2), player_name_attr);
		self.win.addstr("{0:>4}".format(state.s2), score_attr);

		if state.round_type == 'L':
			# If a letter is in the bottom rack, don't display it
			# in the top rack
			
			letters_rack_list = list(state.letters_rack);

			# Build up bottom_rack as we go: add as uppercase
			# letters if they're in the selection, lowercase if
			# they aren't.
			bottom_rack = [];
			for l in state.bottom_rack.upper():
				if l in letters_rack_list:
					ind = letters_rack_list.index(l);
					letters_rack_list[ind] = " ";
					bottom_rack.append(l);
				else:
					bottom_rack.append(l.lower());
			while len(letters_rack_list) < 9:
				letters_rack_list.append(' ');

			rack_x = (self.width - (len(letters_rack_list) * 2 + 1)) / 2;
			draw_rectangle(self.win, self.letters_y - 1, rack_x - 2, self.letters_y + 1, rack_x + len(letters_rack_list) * 2 + 1 + 1);
			self.win.move(self.letters_y, rack_x);

			for l in letters_rack_list:
				self.win.addstr(" " + l, colour2(curses.COLOR_WHITE, curses.COLOR_BLUE) | curses.A_BOLD);
			self.win.addstr(" ", colour2(curses.COLOR_WHITE, curses.COLOR_BLUE) | curses.A_BOLD);

			if bottom_rack != []:
				self.win.move(self.bottom_rack_y, rack_x);
				padded_bottom_rack = "{0:^9}".format(''.join(bottom_rack));
				attr = colour2(curses.COLOR_WHITE, curses.COLOR_BLUE) | curses.A_BOLD;
				for l in padded_bottom_rack:
					self.win.addstr(" ", attr);
					# Show phantom letters in red
					if l.islower():
						self.win.addstr(l.upper(), colour2(curses.COLOR_WHITE, curses.COLOR_RED) | curses.A_BOLD);
					else:
						self.win.addstr(l, attr);
				self.win.addstr(" ", attr);

				draw_rectangle(self.win, self.bottom_rack_y - 1, rack_x - 2, self.bottom_rack_y + 1, rack_x + len(padded_bottom_rack) * 2 + 1 + 1);
				if self.letters_y + 2 == self.bottom_rack_y:
					self.win.addch(self.letters_y + 1, rack_x - 2, curses.ACS_LTEE);
					self.win.addch(self.letters_y + 1, rack_x + len(padded_bottom_rack) * 2 + 1 + 1, curses.ACS_RTEE);

		elif state.round_type == 'N':
			self.win.move(self.number_target_y, (self.width - 5) / 2);
			if state.numbers_target > 0:
				self.win.addstr(" {0:>3d} ".format(state.numbers_target), curses.A_BOLD | colour2(curses.COLOR_YELLOW, curses.COLOR_BLACK));

			
			number_rack = list(state.numbers_rack);

			num_digits = 0;
			for n in number_rack:
				num_digits += len(str(n));

			rack_start_x = (self.width - (num_digits + 2 * len(number_rack) + len(number_rack) - 1)) / 2;
			if rack_start_x < 0:
				rack_start_x = 0;

			self.win.move(self.number_rack_y, rack_start_x);

			num_index = 0;
			for n in number_rack:
				if num_index > 0:
					self.win.addstr(" ");
				self.win.addstr(" {0:d} ".format(int(n)), colour2(curses.COLOR_WHITE, curses.COLOR_BLUE) | curses.A_BOLD);
				num_index += 1;
		elif state.round_type == 'C':
			att = colour2(curses.COLOR_WHITE, curses.COLOR_BLUE);
			conundrum_x = (self.width - (len(state.conundrum_scramble) * 2 + 1)) / 2;

			# Draw necessary rectangles
			draw_rectangle(self.win, self.top_flippything_y - 1, conundrum_x - 2, self.top_flippything_y + 1, conundrum_x + len(state.conundrum_scramble) * 2 + 1 + 1);
			draw_rectangle(self.win, self.bottom_flippything_y - 1, conundrum_x - 2, self.bottom_flippything_y + 1, conundrum_x + len(state.conundrum_scramble) * 2 + 1 + 1);
			if self.top_flippything_y + 2 == self.bottom_flippything_y:
				self.win.addch(self.top_flippything_y + 1, conundrum_x - 2, curses.ACS_LTEE);
				self.win.addch(self.top_flippything_y + 1, conundrum_x + len(state.conundrum_scramble) * 2 + 1 + 1, curses.ACS_RTEE);

			# Draw the conundrum scramble flippything
			self.win.move(self.top_flippything_y, conundrum_x);
			if state.conundrum_top_state > 0:
				for l in state.conundrum_scramble:
					self.win.addstr(" ", att | curses.A_BOLD);
					self.win.addstr(l, att | curses.A_BOLD);

				self.win.addstr(" ", att);
			else:
				self.win.addstr("     COUNTDOWN     ", att);

			# And the solution flippything
			self.win.move(self.bottom_flippything_y, (self.width - (len(state.conundrum_solution) * 2 + 1)) / 2);
			if state.conundrum_bottom_state == 0:
				self.win.addstr("     CONUNDRUM     ", att);
			else:
				if state.conundrum_bottom_state == 1:
					word = state.conundrum_solution;
					att = colour2(curses.COLOR_WHITE, curses.COLOR_BLUE) | curses.A_BOLD;
				else:
					word = "INCORRECT";
					att = colour2(curses.COLOR_WHITE, curses.COLOR_RED) | curses.A_BOLD;
				for l in word:
					self.win.addstr(" ", att);
					self.win.addstr(l, att);
				self.win.addstr(" ", att);

		self.win.refresh();

################################################################################

def listener_thread_fn(sock, dialogue):
	while True:
		conn, addr = sock.accept();
		connected_sockets_lock.acquire();
		connected_sockets.append(conn);
		dialogue_write(dialogue, "Received connection from " + str(addr));
		connected_sockets_lock.release();



################################################################################

# SERVER FUNCTIONS

def load_dictionary(filename):
	f = open(filename, "r");
	lines = f.readlines();
	lines = map(lambda x: x.rstrip().upper(), lines);
	f.close();
	return lines;

def dialogue_write(dialogue, data):
	dialogue.addstr(data);
	dialogue.addstr("\n");
	dialogue.refresh();

def dialogue_prompt(dialogue, prompt):
	dialogue.addstr(prompt);
	dialogue.refresh();
	curses.echo();
#	curses.curs_set(1);
	answer = dialogue.getstr();
#	curses.curs_set(0);
	curses.noecho();
	return answer;

def broadcast_message(msg):
	connected_sockets_lock.acquire();
	socklist = connected_sockets[:];
	connected_sockets_lock.release();

	for sock in socklist:
		try:
			sock.sendall(msg);
		except:
			connected_sockets_lock.acquire();
			if sock in connected_sockets:
				connected_sockets.remove(sock);
			connected_sockets_lock.release();
	return 0;

def broadcast_state(state):
	pickled_state = pickle.dumps(state);
	return broadcast_message(str(len(pickled_state)) + "\n" + pickled_state);

def start_clock():
	broadcast_message("A");

def pause_clock():
	broadcast_message("B");

def resume_clock():
	broadcast_message("C");


def set_conundrum(state, view, dialogue):
	scramble = dialogue_prompt(dialogue, "Conundrum scramble: ");
	scramble = scramble.upper();
	if scramble == "":
		dialogue_write(dialogue, "Aborted.");
		return 1;
	solution = dialogue_prompt(dialogue, "Conundrum solution: ");
	solution = solution.upper();
	if solution == "":
		dialogue_write(dialogue, "Aborted.");
		return 1;
	scramble_list = list(scramble);
	solution_list = list(solution);
	scramble_list.sort();
	solution_list.sort();
	if scramble_list != solution_list:
		dialogue_write(dialogue, "Scramble and solution are not anagrams of each other: not proceeding.");
		return 1;
	state.conundrum_scramble = scramble;
	state.conundrum_solution = solution;
	state.conundrum_top_state = 0;
	state.conundrum_bottom_state = 0;
	dialogue_write(dialogue, "Done.");
	return 0;

def conundrum_round(state, view, dialogue):
	if state.conundrum_scramble == "" or state.conundrum_solution == "":
		set_conundrum(state, view, dialogue);
		if state.conundrum_scramble == "" or state.conundrum_solution == "":
			return 1;
	
	state.round_type = 'C';
	state.conundrum_top_state = 0;
	state.conundrum_bottom_state = 0;

	dialogue_write(dialogue, "Press S to reveal and start clock.");
	return 0;

def numbers_round(state, view, dialogue):
	state.round_type = 'N';
	state.numbers_rack = ();
	state.numbers_target = -1;

	broadcast_state(state);
	view.draw(state);

	numstr = dialogue_prompt(dialogue, "Enter six numbers separated by spaces: ");
	if numstr == "":
		dialogue_write(dialogue, "Aborted.");
		return 1;

	numstr = re.sub("  *", " ", numstr);
	numbers = numstr.split(" ");
	if len(numbers) != 6:
		dialogue_write(dialogue, "That's not six numbers.");
		return 1;

	for n in numbers:
		try:
			if int(n) < 0:
				dialogue_write(dialogue, n + " is not a positive number.");
				return 1;
		except:
			dialogue_write(dialogue, "At least one of those isn't a number.");
			return 1;

	reordered_numbers = [];
	for l in numbers:
		if int(l) > 10:
			reordered_numbers.append(int(l));

	for s in numbers:
		if int(s) <= 10:
			reordered_numbers.append(int(s));

	state.numbers_rack = tuple(reordered_numbers);
	state.numbers_target = -1;
	state.round_type = 'N';
	broadcast_state(state);
	view.draw(state);
	
	numstr = None;
	while numstr == None:
		numstr = dialogue_prompt(dialogue, "Enter target: ");
		try:
			if int(numstr) < 0:
				dialogue_write(dialogue, n + " is not a positive number.");
				numstr = None;
		except:
			dialogue_write(dialogue, "That's not a number.");
			numstr = None;

	# If there are any large numbers in the selection, put them at the
	# start.

	state.numbers_target = int(numstr);

	return 0;

def show_letters_maxes(state, view, dialogue):
	if dictionary == []:
		dialogue_write(dialogue, "No dictionary loaded.");
	if state.round_type == 'L':
		allowable_words = [];
		maxlen = 0;
		rlist_orig = list(state.letters_rack);

		for word in dictionary:
			wlist = list(word);
			rlist = rlist_orig[:];
			for l in wlist:
				if l in rlist:
					rlist.remove(l);
				else:
					break;
			else:
				if len(word) > maxlen:
					maxlen = len(word);
				allowable_words.append(word);

		allowable_words = filter(lambda x : len(x) >= maxlen, allowable_words);
		if allowable_words == []:
			dialogue_write(dialogue, "No words available from this selection.");
		else:
			num_words = 0;
			maxes_str = "";
			for word in allowable_words:
				if num_words > 0:
					maxes_str += ", ";
				maxes_str += word;
				num_words += 1;
			dialogue_write(dialogue, "Maximum " + str(maxlen) + ": " + maxes_str);
	return 0;


def letters_round(state, view, dialogue):
	dialogue_write(dialogue, "Enter letters, then press ENTER.");

	state.round_type = 'L';
	state.letters_rack = "";
	state.bottom_rack = "";

	broadcast_state(state);
	view.draw(state);

	key = curses.ERR;
	while key != ord('\n'):
		key = dialogue.getch();
		if key == curses.KEY_BACKSPACE or key == curses.erasechar():
			if state.letters_rack != "":
				state.letters_rack = state.letters_rack[:-1];
			broadcast_state(state);
			view.draw(state);
		elif (key >= ord('A') and key <= ord('Z')) or (key >= ord('a') and key <= ord('z')):
			letter = chr(key).upper();
			if len(state.letters_rack) < 9:
				state.letters_rack = state.letters_rack + letter;
				broadcast_state(state);
				view.draw(state);
	return 0;


def set_match_info(state, view, dialogue):
	title = dialogue_prompt(dialogue, "Title [" + state.title + "]? ");
	if title != "":
		state.title = title;
	p1 = dialogue_prompt(dialogue, "Player 1 [" + state.p1 + "]? ");
	if p1 != "":
		state.p1 = p1;
	p2 = dialogue_prompt(dialogue, "Player 2 [" + state.p2 + "]? ");
	if p2 != "":
		state.p2 = p2;


def set_score(state, view, dialogue, player):
	if player == 1 or player == 2:
		operation = 0;

		if player == 1:
			answer = dialogue_prompt(dialogue, state.p1 + "'s score (" + str(state.s1) + ")? ");
		elif player == 2:
			answer = dialogue_prompt(dialogue, state.p2 + "'s score (" + str(state.s2) + ")? ");

		if answer == "":
			return;

		if answer[0] == '+':
			operation = 1;
			answer = answer[1:];
		elif answer[0] == '-':
			operation = -1;
			answer = answer[1:];
		else:
			operation = 0;
		
		try:
			score = int(answer);
		except:
			dialogue_write(dialogue, answer + " is not a number.");
			return;
	
		if player == 1:
			if operation == -1:
				state.s1 -= score;
			elif operation == 0:
				state.s1 = score;
			else:
				state.s1 += score;
		else:
			if operation == -1:
				state.s2 -= score;
			elif operation == 0:
				state.s2 = score;
			else:
				state.s2 += score;
	else:
		answer = dialogue_prompt(dialogue, "Score (" + str(state.s1) + "-" + str(state.s2) + ")? ");

		if answer == "":
			return;

		split_score = answer.split("-");
		if len(split_score) == 2 and len(split_score[0]) > 0 and len(split_score[1]) > 0:
			try:
				score1 = int(split_score[0]);
				score2 = int(split_score[1]);
				state.s1 = score1;
				state.s2 = score2;
			except:
				dialogue_write(dialogue, "Invalid score "  + answer);
				return;
		else:
			if answer[0] == '+':
				operation = 1;
				answer = answer[1:];
			elif answer[0] == '-':
				operation = -1;
				answer = answer[1:];
			else:
				operation = 0;

			try:
				score = int(answer);
				if operation == -1:
					state.s1 -= score;
					state.s2 -= score;
				elif operation == 1:
					state.s1 += score;
					state.s2 += score;
				else:
					state.s1 = score;
					state.s2 = score;
			except:
				dialogue_write(dialogue, "Invalid score " + answer);
				return;


################################################################################

server = "localhost";
port = 12012;
client_role = False;
music_file_name = "";
state_file_name = os.environ["HOME"] + "/.livegame_state";
dict_file_name = "";

parser = argparse.ArgumentParser(description="Act as a client or server for a live co-event game.");

parser.add_argument("-s", action="store", dest="server", default="localhost");
parser.add_argument("-p", action="store", dest="port", default="12012");
parser.add_argument("-c", action="store_true", dest="client_role");
parser.add_argument("-m", action="store", dest="music_file_name", default="");
parser.add_argument("-d", action="store", dest="dict_file_name", default="");
parser.add_argument("-b", action="store", dest="background_image_file", default="");
parser.add_argument("-f", action="store", dest="font_file", default="");

opts = parser.parse_args();
server = opts.server;
port = int(opts.port);
client_role = opts.client_role;
music_file_name = opts.music_file_name;
dict_file_name = opts.dict_file_name;
background_image_file = opts.background_image_file;
font_file = opts.font_file;
dictionary = [];

if dict_file_name != "":
	try:
		dictionary = load_dictionary(dict_file_name);
	except:
		print "Couldn't open " + dict_file_name + "\n";
		sys.exit(1);

if client_role:
	screen_width = 800
	screen_height = 600
	music_paused = False;
	resized = False;
	title_bar = True;
	pygame.mixer.pre_init(frequency=48000);
	pygame.init();

	if music_file_name != "":
		pygame.mixer.init();
		sound = pygame.mixer.Sound(music_file_name);
	else:
		sound = None;

	if background_image_file:
		background_image = pygame.image.load(background_image_file);
	else:
		background_image = None;

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
	sock.connect((server, port));

	screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE);

	state = GameState();
	view = GUILiveGameWindow(background_image);
	view.draw(screen, state);
	while True:
		#clear_message(screen);

		try:
			msg_type = state.read_message(sock, 0.5);
		except socket.error, e:
			#display_message(screen, "LOST CONNECTION");
			sock.close();
			time.sleep(5);
			sock = None;
			while sock == None:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
				try:
					sock.connect(server, port);
				except socket.error:
					sock.close();
					sock = None;
					time.sleep(5);
			continue;

		if msg_type == 1:
			if sound != None:
				sound.stop();
				sound.play();
				music_paused = False;
				pygame.mixer.unpause();
		elif msg_type == 2:
			if sound != None:
				if music_paused:
					pygame.mixer.unpause();
				else:
					pygame.mixer.pause();
				music_paused = not(music_paused);
		elif msg_type == 3:
			if sound != None:
				pygame.mixer.unpause();
				music_paused = False;

		if resized:
			flags = pygame.RESIZABLE;
			if not title_bar:
				flags |= pygame.NOFRAME;

			screen = pygame.display.set_mode((screen_width, screen_height), flags);
			view.rescale_background(screen);
			resized = False;

		if msg_type != -1:
			view.draw(screen, state);
			pygame.display.flip();

		pygame.event.pump();
		event = pygame.event.poll();
		while event.type != pygame.NOEVENT:
			if event.type == pygame.VIDEORESIZE:
				screen_width = max(10, event.w)
				screen_height = max(10, event.h)
				resized = True
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_q:
					sys.exit(0);
				elif event.key == pygame.K_f:
					title_bar = not(title_bar)
					resized = True
			event = pygame.event.poll()
else:
	# Initialise ncurses
	mainwin = curses.initscr();
	curses.start_color();
	curses.use_default_colors();

	# Initialise colour pairs
	for fg in range(0, 8):
		for bg in range(0, 8):
			if bg == 0:
				curses.init_pair(bg * 8 + fg, fg, -1);
			elif bg != 0 or fg != 0:
				curses.init_pair(bg * 8 + fg, fg, bg);

	(screen_height, screen_width) = mainwin.getmaxyx();

	curses.noecho();
	curses.cbreak();
	key = curses.ERR;
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1);
		sock.bind((server, port));
		sock.listen(1);

		gamewin = curses.newwin(12, screen_width, 0, 0);
		helpwin = curses.newwin(4, screen_width, 12, 0);
		dialogue = curses.newwin(screen_height - 17, screen_width, 17, 0);

		dialogue.scrollok(True);
		dialogue.idlok(True);
		dialogue.keypad(1);

		helpwin.addstr(0, 0, " L   letters round        1/2  set player score      S      start clock");
		helpwin.addstr(1, 0, " N   numbers round        B    set both scores       SPACE  stop clock"); 
		helpwin.addstr(2, 0, " C   conundrum round      D    load dictionary       T      set title/players");
		helpwin.addstr(3, 0, " SHIFT-C set conundrum    W    check word            M      show word maxes");
		helpwin.refresh();

		listener_thread = threading.Thread(target=listener_thread_fn, name="Listener Thread", args=(sock,dialogue));
		listener_thread.daemon = True;
		listener_thread.start();
		state = GameState();
		try:
			state.load(state_file_name);
		except:
			pass;

		view = CursesLiveGameWindow(gamewin);
		view.draw(state);
	except:
		curses.endwin();
		raise;

	this_con_revealed = True;
	prompt = True;

	while True:
		if prompt:
			dialogue.addstr(">>> ");
			dialogue.refresh();
			prompt = False;
		curses.halfdelay(1);
		key = dialogue.getch();
		curses.cbreak();
		try:
			start_clock_prompt = False;
			if key == curses.ERR:
				pass;
			else:
				prompt = True;
				dialogue_write(dialogue, "");
				if key == ord('c'):
					if this_con_revealed:
						set_conundrum(state, view, dialogue);
					if conundrum_round(state, view, dialogue) == 0:
						this_con_revealed = False;
				elif key == ord('C'):
					if set_conundrum(state, view, dialogue) == 0:
						this_con_revealed = False;
				elif key == ord('n'):
					if numbers_round(state, view, dialogue) == 0:
						start_clock_prompt = True;
				elif key == ord('l'):
					if letters_round(state, view, dialogue) == 0:
						start_clock_prompt = True;
				elif key == ord('k'):
					answer = dialogue_prompt(dialogue, "Bottom rack? ");
					state.bottom_rack = answer;
				elif key == ord('s'):
					if state.round_type == 'C':
						if state.conundrum_top_state == 0:
							state.reveal_conundrum_scramble();
						dialogue_write(dialogue, "[SPACE] to stop clock, [R] to reveal answer.");
					start_clock();
				elif key == ord('i'):
					if state.round_type == 'C':
						state.reveal_conundrum_incorrect();
				elif key == ord('r'):
					if state.round_type == 'C':
						state.reveal_conundrum_answer();
						this_con_revealed = True;
				elif key == ord('p') or key == ord(' '):
					pause_clock();
					if state.round_type == 'C':
						dialogue_write(dialogue, "[R] to reveal correct answer, [SPACE] to resume/stop clock.");
				elif key == ord('o'):
					if state.round_type == 'C' and state.conundrum_bottom_state == 2:
						state.conundrum_bottom_state = 0;
					resume_clock();
				elif key == ord('q'):
					answer = dialogue_prompt(dialogue, "Are you sure you want to quit [Y/N]? ");
					if len(answer) > 0 and answer[0].upper() == 'Y':
						break;
				elif key == ord('1'):
					set_score(state, view, dialogue, 1);
				elif key == ord('!'):
					state.s1 += 10;
				elif key == ord("\""):
					state.s2 += 10;
				elif key == ord('2'):
					set_score(state, view, dialogue, 2);
				elif key == ord('b'):
					set_score(state, view, dialogue, 3);
				elif key == ord('t'):
					set_match_info(state, view, dialogue);
				elif key == ord('d'):
					answer = dialogue_prompt(dialogue, "Dictionary file [" + dict_file_name + "]? ");
					if answer == "":
						answer = dict_file_name;
					try:
						dictionary = load_dictionary(answer);
						dict_file_name = answer;
						dialogue_write(dialogue, str(len(dictionary)) + " words loaded from " + dict_file_name);
					except:
						dialogue_write(dialogue, "Couldn't load " + answer);
				elif key == ord('w'):
					if dictionary == []:
						dialogue_write(dialogue, "Can't check words as no dictionary loaded.");
					else:
						answer = dialogue_prompt(dialogue, "Enter word to check: ");
						if answer != "":
							if answer.upper() in dictionary:
								dialogue_write(dialogue, answer + " is VALID.");
							else:
								dialogue_write(dialogue, answer + " is INVALID.");

				elif key == 5: # ^E
					answer = dialogue_prompt(dialogue, "Reset game state, forgetting player names, scores and everything [y/N]? ");
					if answer != "" and answer[0].upper() == 'Y':
						state.set_state(GameState());
						dialogue_write(dialogue, "Done.");
				elif key == 24: # ^X
					state.round_type = '';
					state.letters_rack = "";
				elif key == ord('m'):
					if state.round_type == 'L':
						show_letters_maxes(state, view, dialogue);
				elif key < 256:
					if chr(key) in string.printable:
						keystr = chr(key);
					elif key <= ord(' '):
						keystr = "^" + chr(key + ord('A') - 1);
					else:
						keystr = "";
					dialogue_write(dialogue, "Unknown command " + keystr);

				broadcast_state(state);
				state.save(state_file_name);
				view.draw(state);
				dialogue.cursyncup();
				dialogue.refresh();

				if start_clock_prompt:
					answer = dialogue_prompt(dialogue, "Start clock [Y/n]? ");
					if answer == "" or answer[0].upper() != 'N':
						start_clock();
		except curses.error:
			key = curses.ERR;
		except:
			curses.endwin();
			raise;
	curses.endwin();

sys.exit(0);
