import numpy as np
from numba import jit

@jit(nopython=True)
def run_gr4j(x, p, e, q, s, uh1, uh2, l, m):
    x1, x2, x3, x4 = x[:4]
    if len(x) > 4:
        d = x[4]
    else:
        d = 0
    d0 = int(d)
    d1 = d0 + 1
    w1 = d - float(d0)
    w0 = 1. - w1
    for t in range(p.size):
        if p[t] > e[t]:
            pn = p[t] - e[t]
            en = 0.
            tmp = s[0] / x1
            ps = x1 * (1. - tmp * tmp) * np.tanh(pn / x1) / (1. + tmp * np.tanh(pn / x1))
            s[0] += ps
        elif p[t] < e[t]:
            ps = 0.
            pn = 0.
            en = e[t] - p[t]
            tmp = s[0] / x1
            es = s[0] * (2. - tmp) * np.tanh(en / x1) / (1. + (1. - tmp) * np.tanh(en / x1))
            tmp = s[0] - es
            if tmp > 0.:
                s[0] = tmp
            else:
                s[0] = 0.
        else:
            pn = 0.
            en = 0.
            ps = 0.
        tmp = (4. * s[0] / (9. * x1))
        perc = s[0] * (1. - (1. + tmp * tmp * tmp * tmp) ** (-1. / 4.))
        s[0] -= perc
        pr_0 = perc + pn - ps
        q9 = 0.
        q1 = 0.
        for i in range(m):
            if i == 0:
                pr_i = pr_0
            else:
                pr_i = s[2 + i - 1]
            if i < l:
                q9 += uh1[i] * pr_i;
            q1 += uh2[i] * pr_i;
        q9 *= 0.9
        q1 *= 0.1
        f = x2 * ((s[1] / x3) ** (7. / 2.))
        tmp = s[1] + q9 + f
        if tmp > 0.:
            s[1] = tmp
        else:
            s[1] = 0.
        tmp = s[1] / x3
        qr = s[1] * (1. - ((1. + tmp * tmp * tmp * tmp) ** (-1. / 4.)))
        s[1] -= qr
        tmp = q1 + f
        if tmp > 0.:
            qd = tmp
        else:
            qd = 0.
        if s.size > 2:
            s[3:] = s[2:-1]
            s[2] = pr_0
        # delayer:
        qt = qr + qd
        if t + d0 < p.size:
            q[t + d0] += w0 * qt
            if t + d1 < p.size:
                q[t + d1] += w1 * qt

class gr4j:
    """
    GR4J model class.
    """
    def sh1(self, t):
        x4 = self.x[3]
        if t == 0:
            res = 0.
        elif t < x4:
            res = (float(t) / x4) ** (5. / 2.)
        else:
            res = 1.
        return res
    def sh2(self, t):
        x4 = self.x[3]
        if t == 0:
            res = 0.
        elif t < x4:
            res = 0.5 * ((float(t) / x4) ** (5. / 2.))
        elif t < 2. * x4:
            res = 1. - 0.5 * ((2. - float(t) / x4) ** (5. / 2.))
        else:
            res = 1.
        return res
    def uh1(self, j):
        return self.sh1(j) - self.sh1(j - 1)
    def uh2(self, j):
        return self.sh2(j) - self.sh2(j - 1)
    def __init__(self, x=None):
        self.p = None
        self.e = None
        if not x is None:
            self.set_x(x)
    def set_x(self, x):
        x1, x2, x3, x4 = x[:4]
        self.x = np.zeros(5)
        self.x[:len(x)] = x[:len(x)]
        if x[0] <= 0 or x[2] <= 0 or x[3] <= 0:
            return self
        self.s = np.empty(2 + int(2. * x4))
        self.s[0] = x1 / 2.
        self.s[1] = x3 / 2.
        self.s[2:] = 0.
        self.l = int(x4) + 1
        self.m = int(2. * x4) + 1
        self.uh1_array = np.empty(self.l)
        self.uh2_array = np.empty(self.m)
        for i in range(self.m):
            if i < self.l:
                self.uh1_array[i] = self.uh1(i + 1)
            self.uh2_array[i] = self.uh2(i + 1)
        return self
    def run(self, pe=None, x=None):
        if pe is None:
            pe = [self.p, self.e]
        if x is not None:
            self.set_x(x)
        q = np.zeros_like(pe[0])
        if self.x[0] <= 0 or self.x[2] <= 0 or self.x[3] <= 0:
            q[:] = np.inf
            return q
        run_gr4j(self.x, pe[0], pe[1], q, self.s, self.uh1_array, self.uh2_array, self.l, self.m)
        return q
    def set_pe(self, pe):
        self.p = pe[0]
        self.e = pe[1]
        return self

@jit(nopython=True)
def run_delay(d, qin, qout):
    if d < 0:
        qout[:] = np.inf
    else:
        for t in range(qin.size):
            d0 = int(d)
            d1 = d0 + 1
            w1 = d - float(d0)
            w0 = 1. - w1
            if t + d0 < qin.size:
                qout[t + d0] += w0 * qin[t]
                if t + d1 < qin.size:
                    qout[t + d1] += w1 * qin[t]

class delay:
    def __init__(self, d=None):
        self.qin = None
        if d is not None:
            self.set_d(d)
    def set_d(self, d):
        self.d = float(d)
    def set_qin(self, qin):
        self.qin = qin
        return self
    def run(self, qin=None, d=None):
        if qin is None:
            qin = self.qin
        if d is not None:
            self.set_d(d)
        qout = np.zeros_like(qin)
        run_delay(self.d, qin, qout)
        return qout
