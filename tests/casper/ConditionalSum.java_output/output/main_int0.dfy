/***************************** UTIL Functions *******************************/
function str_equal(val1: int, val2: int) : bool
{
  val1 == val2
}

/***************************** DO MAP ***************************************/
function domap (data: seq<int>, i0: int, i: int, loop0: bool) : seq<(int, int)>
  requires 0 <= i < |data|
  ensures domap(data, i0, i, loop0) == [(0,data[i])]
{
  [(0,data[i])]
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
      doreduce(input, key) == input[0].1 + doreduce(input[1..], key)
  ensures (|input| > 0 && input[0].0 != key) ==> 
      doreduce(input, key) == doreduce(input[1..], key)
{
  if input == [] then 0 
  else if input[0].0 == key then input[0].1 + doreduce(input[1..], key)
  else doreduce(input[1..], key)
}

/******************************* HARNESS ************************************/  

lemma Lemma2 (a: seq<(int, int)>, b: seq<(int, int)>, key: int)
  ensures doreduce(a+b,key) == (doreduce(b,key) + doreduce(a,key))
{
  if a != []
  {
    Lemma2(a[1..], b, key);
    assert a + b == [a[0]] + (a[1..] + b);
  }
}

lemma Lemma (data: seq<int>, sum: int, sum0: int, i: int, i0: int, loop0: bool)
  
  requires loopInvariant(data,sum,0,i,0,loop0) && (i<|data|)
  
{
  assert mapper(data, i0, i+1, loop0) == domap(data, i0, i, loop0) + mapper(data, i0, i, loop0);

  assert doreduce(domap(data, i0, i, loop0),0) == data[i];
	Lemma2(domap(data, i0, i, loop0),mapper(data, i0, i, loop0),0);
	assert doreduce(mapper(data, i0, i+1, loop0),0) == doreduce(domap(data, i0, i, loop0),0) + doreduce(mapper(data, i0, i, loop0),0);

	
}

predicate loopInvariant (data: seq<int>, sum: int, sum0: int, i: int, i0: int, loop0: bool)
  
{
  0 <= i <= |data| &&
	sum == doreduce(mapper(data,i0,i,loop0),0)
}

predicate postCondition (data: seq<int>, sum: int, sum0: int, i: int, i0: int, loop0: bool)
  
{
  i == |data| &&
	sum == doreduce(mapper(data,i0,i,loop0),0)
}

method harness (data: seq<int>, sum: int, i: int)
  
{
  var sum0 := 0;
	var loop0 := false;
	var i0 := 0;
	
  assert loopInvariant(data,0,0,0,0,loop0);

	if(loopInvariant(data,sum,0,i,0,loop0) && (i<|data|))
	{
		Lemma(data,sum,0,i,0,loop0);
		var ind_i := i;
		ind_i := (i+1);
		var ind_sum := sum;
		if((data[i]<100))
		{
			ind_sum := (sum+data[i]);
		} else 
		{
			ind_sum := sum;
		}
		assert loopInvariant(data,ind_sum,0,ind_i,0,loop0);
	}

	if(loopInvariant(data,sum,0,i,0,loop0) && !(i<|data|))
	{
		assert postCondition(data,sum,0,i,0,loop0);
	}
}