/***************************** UTIL Functions *******************************/
function str_equal(val1: int, val2: int) : bool
{
  val1 == val2
}

/***************************** DO MAP ***************************************/
function domap (data: seq<int>, i0: int, i: int, loop0: bool) : seq<(int, int)>
  requires 0 <= i < |data|
  ensures domap(data, i0, i, loop0) == [(0,1)]
{
  [(0,1)]
}

/***************************** MAPPER ***************************************/

function mapper (data: seq<int>, i0: int, i: int, loop0: bool) : seq<(int, int)>
  requires 0 <= i <= |data|
{
  if i == 0 then []
  else domap(data, i0, i-1, loop0) + mapper(data, i0, i-1, loop0)
}

/***************************** DO REDUCE ************************************/

function doreduce(input: seq<(int, int)>, key: int) : int
  ensures (|input| > 0 && input[0].0 == key) ==> 
      doreduce(input, key) == doreduce(input[1..], key) + input[0].1
  ensures (|input| > 0 && input[0].0 != key) ==> 
      doreduce(input, key) == doreduce(input[1..], key)
{
  if input == [] then 0 
  else if input[0].0 == key then doreduce(input[1..], key) + input[0].1
  else doreduce(input[1..], key)
}

/******************************* HARNESS ************************************/  

lemma Lemma2 (a: seq<(int, int)>, b: seq<(int, int)>, key: int)
  ensures doreduce(a+b,key) == (doreduce(a,key) + doreduce(b,key))
{
  if a != []
  {
    Lemma2(a[1..], b, key);
    assert a + b == [a[0]] + (a[1..] + b);
  }
}

lemma Lemma (data: seq<int>, count: int, count0: int, i: int, i0: int, loop0: bool)
  
  requires loopInvariant(data,count,0,i,0,loop0) && (i<|data|)
  
{
  assert mapper(data, i0, i+1, loop0) == domap(data, i0, i, loop0) + mapper(data, i0, i, loop0);

  assert doreduce(domap(data, i0, i, loop0),0) == 1;
	Lemma2(domap(data, i0, i, loop0),mapper(data, i0, i, loop0),0);
	assert doreduce(mapper(data, i0, i+1, loop0),0) == doreduce(mapper(data, i0, i, loop0),0) + doreduce(domap(data, i0, i, loop0),0);

	
}

predicate loopInvariant (data: seq<int>, count: int, count0: int, i: int, i0: int, loop0: bool)
  
{
  0 <= i <= |data| &&
	count == doreduce(mapper(data,i0,i,loop0),0)
}

predicate postCondition (data: seq<int>, count: int, count0: int, i: int, i0: int, loop0: bool)
  
{
  i == |data| &&
	count == doreduce(mapper(data,i0,i,loop0),0)
}

method harness (data: seq<int>, count: int, i: int)
  
{
  var count0 := 0;
	var loop0 := false;
	var i0 := 0;
	
  assert loopInvariant(data,0,0,0,0,loop0);

	if(loopInvariant(data,count,0,i,0,loop0) && (i<|data|))
	{
		Lemma(data,count,0,i,0,loop0);
		var ind_count := count;
		if((data[i]<100))
		{
			ind_count := (count+1);
		} else 
		{
			ind_count := count;
		}
		var ind_i := i;
		ind_i := (i+1);
		assert loopInvariant(data,ind_count,0,ind_i,0,loop0);
	}

	if(loopInvariant(data,count,0,i,0,loop0) && !(i<|data|))
	{
		assert postCondition(data,count,0,i,0,loop0);
	}
}