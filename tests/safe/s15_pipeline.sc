// expect: safe
own int* create() {
    own int* r = alloc(4);
    *r = 0;
    return r;
}
void fill(int* p, int v) {
    *p = v;
}
int twice(int* p) {
    return *p * 2;
}
void destroy(own int* p) {
    free(p);
}
int main() {
    own int* x = create();
    fill(x, 21);
    print(twice(x));
    destroy(x);
    return 0;
}
