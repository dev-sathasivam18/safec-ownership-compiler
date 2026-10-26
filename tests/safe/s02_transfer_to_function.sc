// expect: safe
void consume(own int* q) {
    print(*q);
    free(q);
}
int main() {
    own int* p = alloc(4);
    *p = 7;
    consume(p);
    return 0;
}
