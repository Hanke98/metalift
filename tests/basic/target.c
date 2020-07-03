/* target language definition: each construct is abstracted into
   function prefixed with _ */

int _addOne (int i) {
  return i + 1;
}

int _ite (int a, int b, int c, int d) {
  if (a > b) 
    return c;
  else
    return d;
}

/* returns end */
int _sum (int end) {
  if (end > 0)
    return 1 + _sum(end - 1);
  else
    return 0;
}

