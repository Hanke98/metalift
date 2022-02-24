#include <map>

template <typename T1, typename T2>
struct dict
{
	std::map<T1,T2> contents;

};

template <typename T1, typename T2>
using Map = dict<T1,T2> *;

template <class T1, class T2>
Map<T1,T2> newMap()
{
	return new dict<T1,T2>();
}

// mapinsert old implementation
// template <class T1, class T2>
// Map<T1,T2> mapInsert(Map<T1,T2> m, int k, int v)
// {
// 	m->contents[k] = v;
// 	return m;
	
// }

// template <class T1, class T2>
// Map<T1,T2> mapInsert(Map<T1,T2> m, int k, int v)
// {
	
// 	Map<T1,T2> m2 = newMap<T1,T2>();
// 	m2->contents.insert(m->contents.begin(), m->contents.end());
// 	m2->contents[k] = v;
// 	return m2;
	
// }
template <class T1, class T2>
Map<T1,T2> mapInsert(Map<T1,T2> m, int k, int v)
{
	
	Map<T1,T2> m2 = newMap<T1,T2>();
	auto iter = m->contents.begin();
	while(iter != m->contents.end()){
		m2->contents[iter->first] = iter->second;
	}
	m2->contents[k] = v;
	return m2;
	
}


template <class T1, class T2>
int mapSize(Map<T1,T2> m)
{
	return m->contents.size();
}

template <class T1, class T2>
int mapContains(Map<T1,T2> m, int key)
{
	if (m->contents.count(key) == 0)
		return 0;
	else
		return 1;
}

template <class T1, class T2>
int mapGet(Map<T1,T2> m, int k)
{
	
	return m->contents[k];
}
