(define-sort Map (K V) (Array K V))

(define-fun newMap () (Map Int Int)
  ((as const (Array Int Int)) 0))

(define-fun mapGet ((m (Map Int Int)) (k Int)) Int
  (select m k))

(define-fun mapInsert ((m (Map Int Int)) (k Int) (v Int)) (Map Int Int)
  (store m k v))

(define-fun mapContains ((m (Map Int Int)) (key Int)) Int
(ite (= (select m key) 0) 0 1))