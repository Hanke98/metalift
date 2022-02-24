#include "maps.h"

int test(int x, int y)
{
	Map<int,int> m = newMap<int,int>();

	m = mapInsert(m, x, 2*x);
	m = mapInsert(m, y, 2*y);
	
	int result = mapGet(m,x) + mapGet(m,y);
	return result;
	
}