
def handle_add_two_ints(req, res=None):
  sum_val = req.a+req.b
  print ("Returning [ %s + %s = %s]" % (req.a, req.b, sum_val))

  if res: res.sum = sum_val
  else: res = sum_val

  return res

def handle_add_two_ints2(req, res):
  res.sum = req.a+req.b
  print ("Returning [ %s + %s = %s]" % (req.a, req.b, res.sum))
  return res
