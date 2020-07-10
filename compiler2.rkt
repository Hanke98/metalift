#lang rosette/safe

(require rosette/lib/angelic rosette/lib/match rosette/lib/synthax)

; sum = 0;
; for (int i = 0; i < 10; ++i)
;   sum++

(struct _lte (arg1 arg2) #:transparent)
(struct _eq (arg1 arg2) #:transparent)
(struct _and (arg1 arg2) #:transparent)
(struct loc (id) #:transparent)

; true invariant:
; i <= 10 && sum = i

; version 1: generate conjunction up to recursive depth, where each leaf
; is either of the form i <= <some int> or (sum|i) = (sum|i)
(define (inv-gen i sum depth)
    (cond
    [(<= depth 0)
     (choose* (_lte i (?? integer?)) (_eq (choose* sum i) (choose* sum i)))]

    [else
     (choose*
      (inv-gen i sum 0) ; early bailout if needed
      (_and (inv-gen i sum (- depth 1)) (inv-gen i sum (- depth 1))))]))


; version 2: same as above but each leaf now has form (sum|i) (=|<=) (sum|i|<some int>)
(define (gen-clause i sum)
  (define left (choose* sum i))
  (define right (choose* sum i (?? integer?)))
  (assert (not (eq? left right))) ; simple heuristic to prune clauses like i = i
  ((choose* _lte _eq) left right))

(define (inv-gen2 i sum depth)
  (cond
    [(<= depth 0)
     (gen-clause i sum)]
     
    [else
     (choose*
      (gen-clause i sum) ; early bailout if needed
      (_and (gen-clause i sum) (inv-gen2 i sum (- depth 1))))]))

; post condition is of the form sum = <some int>
(define (ps-gen sum)
  (_eq sum (?? integer?)))


(define (interpret e env)
  (match e
    [(_lte a1 a2)  (<= (interpret a1 env) (interpret a2 env))]
    [(_eq a1 a2)  (= (interpret a1 env) (interpret a2 env))]
    [(_and a1 a2) (and (interpret a1 env) (interpret a2 env))]
    [(loc i) (vector-ref env i)]
    [_ e]))
                 

(define-symbolic i sum integer?)

; we use de bruijn index as dicts are not supported by rosette
; 0 -> i, 1 -> sum
;(define inv (inv-gen (loc 0) (loc 1) 3))
(define inv (inv-gen2 (loc 0) (loc 1) 100))
(define ps (ps-gen (loc 1)))

(define (generate-asserts)
  ; init
  (assert (interpret inv (vector 0 0)))

  ; preservation
  (assert (implies (and (interpret inv (vector i sum)) (< i 10)) (interpret inv (vector (+ 1 i) (+ 1 sum)))))

  ; termination
  (assert (implies (and (interpret inv (vector i sum)) (not (< i 10))) (interpret ps (vector i sum)))))

(define sol
  (synthesize #:forall (list i sum)
              #:guarantee (generate-asserts)))

; (_and (_lte (loc 0) 10) (_and (_lte (loc 0) 10) (_eq (loc 1) (loc 0))))
(evaluate inv sol)
; (_eq (loc 1) 10)
(evaluate ps sol)                                  