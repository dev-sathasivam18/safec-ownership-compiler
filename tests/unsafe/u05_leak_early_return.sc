// expect: leak
int check(int n) {
    own int* p = alloc(4);
    *p = n;
    if (n < 0) {
        return 0;
    }
    free(p);
    return 1;
}
int main() {
    print(check(5));
    return 0;
}
