// expect: safe
void eat(own int* q) {
    print(*q);
    free(q);
}
int main() {
    int i = 0;
    while (i < 3) {
        own int* t = alloc(4);
        *t = i;
        eat(t);
        i = i + 1;
    }
    return 0;
}
