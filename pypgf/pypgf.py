#-*- coding: utf-8 -*-
# pypgf - Python tools for working with pgf fonts.
# Written in 2012 By Falaina falaina@falaina.net
# To the extent possible under law, the author(s) have dedicated all
# copyright and related and neighboring rights to this software to the
# public domain worldwide. This software is distributed without any
# warranty.  You should have received a copy of the CC0 Public Domain
# Dedication along with this software. If not, see
# <http://creativecommons.org/publicdomain/zero/1.0/>.
from __future__ import print_function
from array import array
from collections import OrderedDict
from bitstring import ConstBitStream
from binascii import unhexlify
from os.path import basename, dirname, join as joinpath, normpath
from pprint import pprint
from abc import ABCMeta, abstractmethod
import sys
import numpy as np
import logging

# Directories
FONT_DIR = normpath(joinpath(dirname(__file__), '..', 'fonts'))
TMP_DIR  = normpath(joinpath(dirname(__file__), '..', 'tmp'))

# Logging stuff
FORMAT = '%(asctime)-15s %(module)-6s %(levelname)-6s %(message)s'
logging.basicConfig(format=FORMAT)
log = logging.getLogger('pypgf')
log.setLevel(logging.DEBUG)


class BinaryField(object):
   def __init__(self, name, fmt_string, offset=None):
      """ 
      Creates a BinaryField.
      Offset is not strictly necessary, but will allow validation during parsing
      """
      self.name = name
      self.fmt_string = fmt_string
      self.offset     = offset

   def __repr__(self):
      if self.offset:
         offset = '0x%x' % (self.offset,)
      return 'BinaryField(%s, %s) # %s' % (self.name, self.fmt_string, self.offset)

class BitField(object):
   def __init__(self, name, array, start_pos, num_bits):
      """
      Creates a BitField
      This can be indexed by individual bits
      """
      self.name      = name
      self.start_pos = start_pos
      self.num_bits  = num_bits
      self._array    = array
      
   @property
   def val(self):
      value = 0
      bit_ptr = self.start_pos
      for i in range(self.num_bits):
         bit_shift = bit_ptr % 8
         value += ((self._array[bit_ptr/8] >> bit_shift) & 0x1) << i
         bit_ptr += 1
      return value

   def __int__(self):
      return self.val
      

   def __repr__(self):
      return 'BitField(name=%s, value=%d, offset=%d, num_bits: %d)' % \
          (self.name, self.val, self.start_pos, self.num_bits)

class PGFFile(object): 
   def __init__(self, buf, fontname='font.pgf'):
      self.buf = buf
      self.fontname = fontname

class Table(object):
   def __init__(self, name, bits, entries, bpe):
      self.name    = name
      self.entries = entries
      self.bpe     = bpe
      self.buf     = bits.read('bytes: %d' % (self.size,))
      self._array  = array('B', self.buf)

   @property
   def size(self):
      return ((self.entries * self.bpe + 31) & ~31) / 8

   def __getitem__(self, item):
      if not isinstance(item, int):
         raise IndexError('index must be of type int')

      if item > self.entries:
         raise IndexError('index must be less than list size')

      bit_ptr = item * self.bpe
      log.debug('Starting look up of idx %d from bit ptr %d' % (item, bit_ptr))
      val = 0
      for i in range(self.bpe):
         bit_shift = (bit_ptr % 8)
         val +=  ((self._array[bit_ptr/8] >> bit_shift) & 0x1) << i
         bit_ptr += 1

      log.debug('Value is %d' % (val,))
      return val

   def __repr__(self):
      return 'Table(name=%s, entries=%s, bpe=%s) # size=%s' % \
          (self.name, self.entries, self.bpe, self.size)
   

PGF_BMP_V_ROWS = 0x01
PGF_BMP_H_ROWS = 0x02
PGF_BMP_OVERLAY = 0x03
PGF_EXTRA_METRICS1 = 0x04
PGF_EXTRA_METRICS2 = 0x08
PGF_EXTRA_METRICS3 = 0x10
PGF_CHARGLYPH = 0x20
PGF_SHADGLPH  = 0x40
PGF_WIDTH_MASK = 0xFF
PGF_OPTIONS_MASK = 0x3FFF
PGF_ALIGN_MASK  = 0x600
PGF_SCROLL_MASK = 0x2600
PGF_CACHE_MASK  = 0xC000
PGF_STRING_MASK = 0xFF0000

class GlyphInfo(object):
   _fields_ = [
      ('flags', 6),
      ('magic_no', 7),
      ('shadow_id', 9)      
      ]
   _extensions_ = [
      ('PGF_EXTRA_METRICS1', 0x04, 56),
      ('PGF_EXTRA_METRICS2', 0x08, 56),
      ('PGF_EXTRA_METRICS3', 0x10, 56)
      ]

   def __init__(self, pgf_font, start_pos, array):
      self.pgf_font  = pgf_font
      self.start_pos = start_pos
      self._array    = array

      bit_ptr = start_pos
      for (name, bits) in self._fields_:
         bf = BitField(name, array, bit_ptr, bits)
         bit_ptr += bits
         self.__dict__[name] = bf.val

      flags = self.flags
      bit_ptr += 24
      for (name, bit, size) in self._extensions_:
         if (flags & bit):
            log.debug('%s set' % (name,))
         else:
            log.debug('%s not set, adding %d' % (name, size))
            log.debug('Mystery: %s' %(hex(BitField(name, array, bit_ptr, 56).val),))
            bit_ptr += size

      adv = BitField('AdvPtr', array, bit_ptr, 8)
      bit_ptr += 8
      
      self.advptr = (adv.val * 2)
      log.debug('adv' + str( pgf_font.tables['adv_tab'][(adv.val) * 2]/16))
      self.horiz_adv = pgf_font.tables['adv_tab'][(adv.val) * 2]

      log.info('Parsed glyph' + str( self))
      self.ptr = bit_ptr / 8

   @property
   def flag_str(self):
      pass

   def __repr__(self):
      return 'Glyph(flags=%x, magic_no=%d, advptr=%x)' % (self.flags, self.magic_no, self.advptr)


class CharInfo(object):
   _fields_ = [
      ('shadow_header', 14),
      ('width',          7),
      ('height',         7),
      ('left',           7),
      ('top',            7)
      ]

   def __init__(self, pgf_font, char, array):
      self.pgf_font = pgf_font
      self.char     = char
      self._array   = array

      idx = pgf_font.tables['charmap'][char - pgf_font.first_glyph]
      charptr = pgf_font.tables['charptr'][idx] * 4 * 8

      log.debug('Using a charptr of %x' % (charptr,))
      bit_ptr = charptr
      self.bitfields = {}

      for (name, bits) in self._fields_:
         bf = BitField(name, array, bit_ptr,  bits)
         self.bitfields = bf
         self.__dict__[name] = bf.val
         bit_ptr += bits

      self.glyph_info = GlyphInfo(pgf_font, bit_ptr, array)
      horiz_rows = (self.glyph_info.flags & PGF_BMP_V_ROWS) != 0
      samples = []
      for i in range(self.height):
         row_samples = []
         samples.append(row_samples)
         for j in range(self.width):
            row_samples.append(0)

      # Decode the glyph bitmap. It's RLE-encoded.
      # If the first nibble < 8, repeat the next nibble n + 1 times
      # if the first nibble >= 8, pass it to the output bitstream
      if self.width and self.height: 
         i = 0
         bit_ptr = self.glyph_info.ptr * 8
         while i <= self.width * self.height:
            bf     = BitField('nibble', array, bit_ptr, 4)
            bit_ptr += 4
            nibble = bf.val
            if nibble < 8:
               value = BitField('niboble-2', array, bit_ptr, 4).val
               bit_ptr += 4
               size  = nibble + 1
            else:
               size  = 16 - nibble
            for j in range(size):
               if nibble >= 8:
                  value = BitField('nibble-3', array, bit_ptr, 4).val
                  bit_ptr += 4
               elif j == 0: pass
               if horiz_rows:
                  xx = i%self.width
                  yy = i/self.width
               else:
                  xx = i/self.height
                  yy = i%self.height
               i += 1
               if i >= self.width * self.height:
                  break

               samples[yy][xx] = (value << 4) | value
         rawn = '\n'.join([''.join([str(x) for x in row]) for row  in samples])
         raw  = ''
         for row in samples:
            for sample in row:
               raw += chr(sample)
                  
         self.samples = samples

      else:
         log.warn('Strange no bmp info for %s' % (self,))

   def __repr__(self):
      char = self.char
      char = unichr(char)
      return 'CharInfo(char="%s", width=%s, height=%s, top=%s, left=%s)' % \
          (char, self.width, self.height, self.top, self.left)
      

class FontData(object):
   def __init__(self, pgf_font, bits, size):
      self.pgf_font = pgf_font
      self.buf = bits.read('bytes: %d' % (size))
      self._array = array('B', self.buf)

   def getFontElem(self, char, bit_ptr, bits):
      bit_ptr = char + bit_ptr
      print(hex(self._array[bit_ptr]))
      val = 0
      for i in range(bits):
         bit_shift = (bit_ptr % 8)
         val += ((self._array[bit_ptr/8] >> bit_shift) & 0x1) << i
         bit_ptr += 1
      return val

   def __getitem__(self, item):
      return CharInfo(self.pgf_font, item, self._array)


class PGFFont(object): 
   _fields_ = [
      ('header_off',   'uintle:16',  0x0),
      ('header_size',  'uintle:16',  0x2),
      ('magic',        'bytes: 4',   0x4),
      ('revision',     'uintle: 32', 0x8),
      ('version',      'uintle: 32', 0xC),
      ('len_charmap',  'uintle: 32', 0x10),
      ('len_charptr',  'uintle: 32', 0x14),
      ('bpe_charmap',  'uintle: 32', 0x18),
      ('bpe_charptr',  'uintle: 32', 0x1C),
      ('unk1_4',       'hex: 32',    0x20),
      ('h_size',       'uintle: 32', 0x24),
      ('v_size',       'uintle: 32', 0x28),
      ('h_res',        'uintle: 32', 0x2C),
      ('v_res',        'uintle: 32', 0x30),
      ('weight',       'hex: 8',     0x34),
      ('fontname',     'bytes:  64', 0x35),
      ('fonttype',     'bytes:  64', 0x75),
      ('unk3_1',       'hex: 8',     0xB5),
      ('first_glyph',  'uintle: 16', 0xB6),
      ('last_glyph',   'uintle: 16', 0xB8),
      ('unk4_34',      'bytes: 34',  0xBA),
      ('maxLeftXAdj',  'uintle: 32', 0xDC),
      ('maxBaseYAdj',  'uintle: 32', 0xE0),
      ('minCentXAdj',  'uintle: 32', 0xE4),
      ('maxTopYAdj',   'uintle: 32', 0xE8),
      ('maxAdvH',      'uintle: 32', 0xEC),
      ('maxAdvV',      'uintle: 32', 0xF0),
      ('maxSizeH',     'uintle: 32', 0xF4),
      ('maxSizeV',     'uintle: 32', 0xF8),
      ('maxGlyphW',    'uintle: 16', 0xFC),
      ('maxGlyphH',    'uintle: 16', 0xFE),
      ('unk5',         'hex:   16',  0x100),
      ('len_dim_tab',  'uintle: 8',  0x102),
      ('len_xadj_tab', 'uintle: 8',  0x103),
      ('len_yadj_tab', 'uintle: 8',  0x104),
      ('len_adv_tab',  'uintle: 8',  0x105),
      ('unk6_102',     'bytes: 102', 0x106),
      ('len_shadmap',  'uintle: 32', 0x16C),
      ('bpe_shadmap',  'uintle: 32', 0x170),
      ('unk7_4',       'uintle: 32', 0x174),
      ('x_shadscale',  'uintle: 32', 0x178),
      ('y_shadscale',  'uintle: 32', 0x17C),
      ('unk8_2',       'hex: 64',    0x180),
      ]

   _int64_tables_ = ['dim_tab', 'xadj_tab', 'yadj_tab', 'adv_tab']
   _tables_       = ['shadmap', 'charmap', 'charptr']
   
   def _validate_parse(self):
      assert self.version == 6,     'Invalid version: %d' % (self.revision)
      assert self.revision in [2, 3], 'Invalid revision: %d' % (self.version)
      assert self.bpe_charmap <= 32, 'Invalid charmap bpe: %d' % (self.bpe_charmap)
      assert self.bpe_charptr <= 32, 'Invalid charptr bpe: %d' % (self.bpe_charptr)
      assert self.first_glyph <= 128, 'Invalid first glyph: %d' % (self.first_glyph)
      assert self.last_glyph <= 65535,'Invalid last glyph: %d' % (self.last_glyph)
      assert self.bpe_shadmap <= 32, 'Invalid shadmap bpe: %d' % (self.bpe_shadmap)      

      assert self.bits.bytepos == self.header_size, \
          '%d header bytes read but stated header size is %d' %\
          (self.bits.bytepos, self.header_size)

   def __new__(cls, font_filename):
      """
      Create a new PGFFont from tile font file specified by 
      `font_filename`
      """
      log.info('Opening font file %s' % (font_filename,))
      bits = ConstBitStream(filename=font_filename)
      obj = super(PGFFont, cls).__new__(cls)
      obj.bits = bits

      log.info('Parsing Font Information')
      obj._size = bits.len / 8
      for (field_name, fmt_str, offset) in PGFFont._fields_:
         assert bits.bytepos == offset, \
             'Incorrect offset while parsing field %s: %x\n%s' % \
             (field_name, bits.bytepos, obj)
         setattr(obj, field_name, bits.read(fmt_str))

      log.info('Parsed %s' % (obj,))
      obj._validate_parse()
      obj.tables = OrderedDict()
      
      for name in PGFFont._int64_tables_:
         entries = getattr(obj, 'len_%s' % (name,))
         buf = bits.read('bytes: %d' % (entries * 2 * 4))
         obj.tables[name] = array('I', buf)

      for name in PGFFont._tables_:
         entries = getattr(obj, 'len_%s' % (name,))
         bpe = 64
         bpe_name = 'bpe_%s' % (name,)
         if bpe_name in obj.__dict__:
            bpe = getattr(obj, bpe_name)
         obj.tables[name] = Table(name, bits, entries, bpe)
         log.debug('Parsed table offset:%x - name=%s - %s' % 
                   (bits.bytepos, name, obj.tables[name]))

      obj.fontdatasize = (bits.len - bits.pos)/8
      obj.fontdata     = FontData(obj, bits, obj.fontdatasize)

      char = obj.tables['charmap'][ord(u'o')]
      return obj

   def get_str_metrics(self, s):
      """
      Get metrics for string `s`
      """
      width64  = 0
      height = 0
      for c in s:
         data = self.fontdata[ord(c)]
         width64 += data.glyph_info.horiz_adv  + (data.left * 64)
         if height < data.top + data.height:
            height = data.top + data.height
      log.debug("str metrics %s" % ((s, width64, height),))
      return (s, width64, height)
      
   def wrap_text(self, s, w, h):
      """
      word wrap string `s` to fit in a rectangle `w` pixels wide by `h` pixels high.
      (It currently ignores the height parameter)
      """
      chunks = []
      words = [self.get_str_metrics(x + ' ') for x in s.split(' ')]
      intervals = []
      cur_start = 0
      while cur_start < len(words):
         cur_width = 0
         cur_end = cur_start
         while cur_end < len(words):
            cur_word = words[cur_end]
            if cur_width + cur_word[1] <= w:
               cur_width += cur_word[1]
            else:
               break
            cur_end += 1
         intervals.append((cur_start, cur_end))
         if cur_start == cur_end:
            assert ValueError('Unable to layout line')
         cur_start = cur_end
      for (start, end) in intervals:
         i = start
         txt = ''
         while i < end:
            txt += words[i][0]
            i += 1
         chunks.append(txt)
      return chunks

   def draw_text(self, s, x, y, img, w, h):
      """
      Draw string `s` to the rectangle specified by `x`, `y`, `w`, `h`.
      `img` must be a sequence with dimensions `w*64`x`h`
      """
      chars = []
      max_top = 0
      for c in s:
         data = self.fontdata[ord(c)]
         chars.append(data)
         if max_top < data.height:
            max_top = data.height

      screen = []
      for i in range(h + 1):
         row = []
         screen.append(row)
         for j in range(w):
            row.append(0)

      cur_x = x
      cur_y = y + max_top

      for c in chars:
         for i in range(c.height):
            for j  in range(c.width):
               for k in range(64):
                  img[(cur_y + i - c.top)][(cur_x) + (j * 64) + k + (c.left * 64)] = c.samples[i][j]
         cur_x += c.glyph_info.horiz_adv  + (c.left * 64)

   def __repr__(self):
      keys = ['first_glyph', 'last_glyph', 'h_res',
              'v_res', 'h_size', 'v_size', 'header_off',
              'maxGlyphH','maxGlyphW', 'maxSizeH', 'maxSizeV']
      out_dict = OrderedDict()
      for key in keys:
         out_dict[key] = self.__dict__[key]
      return str(out_dict)


if '__main__' == __name__:
   # FIXME: This is just a guess at the resolution of the text box
   # Fonts are laid out at 1/64 pixel resolution, so multiply
   # the width by 64
   (w, h) = (475*64, 100)
   if len(sys.argv) <= 1:
      print('Usage: pypgf.py pgf-file "text-to-wrap"')
      exit(-1)

   (filename, text) = sys.argv[1:]
   img = np.zeros((h, w), np.uint8)

   p = PGFFont(filename)
   chunks = p.wrap_text(text, w, h)
   print('chunks', chunks)
   cur_y = 0
   # for chunk in chunks:
   #    p.draw_text(chunk, 0, cur_y, img, w, h)
   #    cur_y += p.maxSizeV/64
