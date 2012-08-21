'''
Created on Aug 20, 2012

@author: tosh7
'''
from logging.handlers import RotatingFileHandler
import os

COMPRESSION_SUPPORTED = {}
try:
  import gzip
  COMPRESSION_SUPPORTED['gz'] = gzip
except ImportError:
  pass
try:
  import zipfile
  COMPRESSION_SUPPORTED['zip'] = zipfile
except ImportError:
  pass


class ZRotatingFileHandler(RotatingFileHandler):
  def __init__(self, *args, **kws):
    print kws
    compress_mode = kws.pop('compress_mode')

    try:
        self.compress_cls = COMPRESSION_SUPPORTED[compress_mode]
    except KeyError:
        raise ValueError('"%s" compression method not supported.' % compress_mode)
     
    RotatingFileHandler.__init__(self, *args, **kws)

  def doRollover(self):
    RotatingFileHandler.doRollover(self)
  
    # Compress the old log.
    for i in range(self.backupCount - 1, 0, -1):
      sfn = "%s.%d.z" % (self.baseFilename, i)
      dfn = "%s.%d.z" % (self.baseFilename, i + 1)
      if os.path.exists(sfn):
        if os.path.exists(dfn):
          os.remove(dfn)
        os.rename(sfn, dfn)
  
      old_log = self.baseFilename + ".1"
      if self.compress_cls == gzip:
        output = self.compress_cls.open(old_log + '.z', 'w')
        with open(old_log) as log:
          output.writelines(log)
          output.close()
      if self.compress_cls == zipfile:
        output = self.compress_cls.ZipFile(old_log + '.z', 'w')
        output.write(old_log)
        output.close() 
      os.remove(old_log)
