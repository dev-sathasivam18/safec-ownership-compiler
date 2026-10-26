// expect: safe
own int* make(int v) {
    own int* r = alloc(4);
    *r = v;
    return r;
}
int main() {
    own int* p = make(9);
    print(*p);
    free(p);
    return 0;
}
