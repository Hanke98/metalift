#include "list.h"

List<int> test(List<int> density0, List<int> density1, int x_max, int x_min, int y_max, int y_min)
{
	
	int k = y_min;
	while(k < y_max)
	{
		int j = x_min;
		while(j < x_max)
		{
			density0 = listSet(density0, (j + (((x_max + 2) - (x_min - 2)) * k)), listGet(density1,j + (((x_max + 2) - (x_min - 2)) * k)));
			j = j + 1;
		}
		k = k + 1;
	}

	return density0;



}