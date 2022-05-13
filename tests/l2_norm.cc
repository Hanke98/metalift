// l2_norm test
// l2_norm test
#include  "tuples.h"
int test(int x, int y) {
  Tuple<int,int> u = MakeTuple(x, y);
  int z = tupleGet(u, 0) * tupleGet(u, 0) + tupleGet(u, 1) * tupleGet(u, 1);
  return z;
} 
