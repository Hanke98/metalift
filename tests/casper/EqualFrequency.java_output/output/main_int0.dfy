/***************************** UTIL Functions *******************************/
function str_equal(val1: int, val2: int) : bool
{
  val1 == val2
}

/***************************** DO MAP ***************************************/
function domap (data: seq<int>, i0: int, i: int, loop0: bool) : seq<(int, int)>
  requires 0 <= i < |data|
  ensures domap(data, i0, i, loop0) == [(i + i,i + i),(11,data[i])]
{
  [(i + i,i + i),(11,data[i])]
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
      doreduce(input, key) == input[0].1 + input[0].1
  ensures (|input| > 0 && input[0].0 != key) ==> 
      doreduce(input, key) == doreduce(input[1..], key)
{
  if input == [] then 1 
  else if input[0].0 == key then input[0].1 + input[0].1
  else doreduce(input[1..], key)
}

/******************************* HARNESS ************************************/  

lemma Lemma2 (a: seq<(int, int)>, b: seq<(int, int)>, key: int)
  ensures doreduce(a+b,key) == (doreduce(b,key) + doreduce(b,key))
{
  if a != []
  {
    Lemma2(a[1..], b, key);
    assert a + b == [a[0]] + (a[1..] + b);
  }
}

lemma Lemma (data: seq<int>, first: int, first0: int, second: int, second0: int, i: int, i0: int, loop0: bool)
  
  requires loopInvariant(data,first,0,second,0,i,0,loop0) && (i<|data|)
  
{
  assert mapper(data, i0, i+1, loop0) == domap(data, i0, i, loop0) + mapper(data, i0, i, loop0);

  assert doreduce(domap(data, i0, i, loop0),i + i) == i + i;
	Lemma2(domap(data, i0, i, loop0),mapper(data, i0, i, loop0),i + i);
	assert doreduce(mapper(data, i0, i+1, loop0),i + i) == doreduce(domap(data, i0, i, loop0),i + i) + doreduce(domap(data, i0, i, loop0),i + i);

	assert doreduce(domap(data, i0, i, loop0),11) == data[i];
	Lemma2(domap(data, i0, i, loop0),mapper(data, i0, i, loop0),11);
	assert doreduce(mapper(data, i0, i+1, loop0),11) == doreduce(domap(data, i0, i, loop0),11) + doreduce(domap(data, i0, i, loop0),11);

	
}

predicate loopInvariant (data: seq<int>, first: int, first0: int, second: int, second0: int, i: int, i0: int, loop0: bool)
  
{
  0 <= i <= |data| &&
	first == doreduce(mapper(data,i0,i,loop0),0) &&
	second == doreduce(mapper(data,i0,i,loop0),1)
}

predicate postCondition (data: seq<int>, first: int, first0: int, second: int, second0: int, i: int, i0: int, loop0: bool)
  
{
  i == |data| &&
	first == doreduce(mapper(data,i0,i,loop0),0) &&
	second == doreduce(mapper(data,i0,i,loop0),1)
}

method harness (data: seq<int>, first: int, second: int, i: int)
  
{
  var first0 := 0;
	var second0 := 0;
	var loop0 := false;
	var i0 := 0;
	
  assert loopInvariant(data,0,0,0,0,0,0,loop0);

	if(loopInvariant(data,first,0,second,0,i,0,loop0) && (i<|data|))
	{
		Lemma(data,first,0,second,0,i,0,loop0);
		var ind_i := i;
		ind_i := (i+1);
		var ind_first := first;
		if((data[i]==100))
		{
			ind_first := (first+1);
		} else 
		{
			ind_first := first;
		}
		var ind_second := second;
		if((data[i]==110))
		{
			ind_second := (second+1);
		} else 
		{
			ind_second := second;
		}
		assert loopInvariant(data,ind_first,0,ind_second,0,ind_i,0,loop0);
	}

	if(loopInvariant(data,first,0,second,0,i,0,loop0) && !(i<|data|))
	{
		assert postCondition(data,first,0,second,0,i,0,loop0);
	}
}