// expect: leak
void drop(own int* q) {
    print(*q);
}
int main() {
    own int* p = alloc(4);
    *p = 8;
    drop(p);
    return 0;
}
