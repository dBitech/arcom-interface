"""Web logging for interference.
   This module implements rudimentary web logging by posting to a Google Form
   which then populates a Google Sheet.
   """
import requests

class LogGoogle(object):
  """Post the event(s) to Google interference log.
     Currently, way too much stuff is hardcoded.  We need a solution
     to this that still keeps it simple for the control operator.
  """
  testing = False
  url_base = ''
  form_data = {}
  user_agent = {
      'User-Agent':'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36'
      }

  def __init__(self, cfg, testing):
    self.testing = testing
    self.url_base = cfg.get('google form', 'url_base')
    for entry in cfg.items('google form'):
      key, value = entry
      self.form_data[key] = value
    self.form_data['draftResponse'] = []
    self.form_data['pageHistory'] = 0
    self.user_agent['Referer'] = self.url_base + '/viewform'

  def log(self, call, location, minutes):
    """Post an interference report to Google form."""
    if not self.testing:
      self.form_data['entry.1984381604'] = call
      self.form_data['entry.773252163'] = location
      self.form_data['entry.530211156'] = 'Yes - ' + str(minutes) + ' min'
      resp = requests.post(self.url_base+'/formResponse',
                           data=self.form_data,
                           headers=self.user_agent)
      if resp.status_code == 200:
        return True, "Action logged to Google."
      else:
        return False, "Logging to Google failed: %s" % resp.status_code
    else:
      return True, "Action NOT logged.  (Testing mode)"
