/* each function is a benchmark to rewrite using the target language */

int simple (int i) {
  int j = i + 2;
  return j;
}

int ite (int a, int b, int c) {
  if (a > 42) 
    return b;
  else
    return c;
}

int combined (int a, int b, int c) {
  if (a > 42) 
    return b + 2;
  else
    return c + 1;
}
                                    
int sum (int n) {
  int sum = 0;
  int i = 0;

  while (i < n) {
    sum++;
    i++;
  }

  return sum;
}
