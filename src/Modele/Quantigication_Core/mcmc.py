import numpy as np
from scipy.stats import beta, norm
from scipy.stats import gamma as gamma_dist
from scipy.fftpack import fft, fftshift
from .rtnorm import rtnorm
from scipy.fftpack import fft, fftshift



# Function to map sparse signal
def map_sparse(TSignal, TZ):
    L, C = TSignal.shape
    Signal_MAP = np.zeros(L)
    for l in range(L):
        # Calculate the sum of the l-th row of TZ and check the condition
        tmp = np.sum(TZ[l, :]) - C / 2
        if tmp > 0:
            # If condition is met, calculate the mean of the l-th row of TSignal
            Signal_MAP[l] = np.mean(TSignal[l, :])
    return Signal_MAP

# Function to sample a random variable w
def sample_w(theta, alpha0, alpha1):
    M = len(theta)
    n1 = np.sum(theta != 0)
    n0 = M - n1

    # Compute coefficients for the beta distribution
    coeff1 = alpha0 + n1
    coeff0 = alpha1 + n0

    # Sample from the beta distribution
    w_out = beta.rvs(coeff1, coeff0)
    return w_out

# Function to compute matrix H
def compute_H(H0, gamma, grps_info, t, sigma2m, epsilon, phi0, phi1):
    M = H0.shape[1]
    H = H0.copy()
    f = np.arange(1/0.001, 1024/0.001 + 1, 1/0.001)  # Frequency range
    for midx in range(M):
        if grps_info == 0:
            # Apply transformation to each column of H0
            H[:, midx] = np.exp(1j * phi0) * FID2Spec(H0[:, midx] * np.exp(-t * ((gamma + sigma2m * t) + 1j * epsilon)))
    return H

# Function to perform Metropolis-Hastings sampling of gamma
def sample_gamma_MH(Observation, VSignal, sigma2, H0, H, gamma, grps_info, t, acc, rej, sigma2_m, epsilon, phi0, phi1, first, last):
    Hstar = H.copy()
    M = H.shape[1]
    # print(np.shape(t))
    pvar = 1  # Proposal variance
    mu_gamma = 5  # Mean of the normal distribution for gamma
    sigma_gamma = 2.5  # Standard deviation of the normal distribution for gamma

    # Propose a new gamma value
    gamma_star = gamma + np.random.randn() * pvar
    for midx in range(M):
        # Compute the proposed new H matrix
        Hstar[:, midx] = fftshift(fft(H0[:, midx] * np.exp(-t * ((gamma_star)))))

    # Compute the probability densities for the current and proposed gamma values
    pdf_old = np.exp(-np.linalg.norm(Observation[first: last] - np.dot(H[first: last, :], VSignal))**2 / sigma2) * norm.pdf(gamma, mu_gamma, np.sqrt(sigma_gamma))
    pdf_star = np.exp(-np.linalg.norm(Observation[first: last] - np.dot(Hstar[first: last, :], VSignal))**2 / sigma2) * norm.pdf(gamma_star, mu_gamma, np.sqrt(sigma_gamma))

    if gamma_star < 0 or gamma_star > 14 or not np.isfinite(gamma_star):
        accept = 0
    else:
        # Acceptance probability
        accept = min(pdf_star / pdf_old, 1)

    # Uniform draw on [0,1]
    urn = np.random.rand()
    accept_result = urn <= accept
    acc += urn <= accept
    rej += urn > accept
    # Update gamma based on acceptance
    gamma = gamma * (urn > accept) + gamma_star * (urn <= accept)

    return gamma, accept_result, acc, rej, pvar


# Function to sample X and Z for a complex operator
def sample_x_l1_Cplx_Operator(X, a, w, sigma2, y, Operator):
    M = len(X)
    Z = np.zeros(M)

    for i in range(M):
        ui1 = np.zeros((M,1))
        ui1[i, 0] = 1

        # Compute the i-th column of the operator matrix
        hi = np.dot(Operator, ui1)
        hi_norm = np.real(np.dot(hi.conj().T, hi))
        hi_norm = max(hi_norm, np.finfo(float).eps)

        X_1i = X.copy()
        X_1i[i] = 0
        # Compute the residual error
        ei = y - Operator @ X_1i
        hiTei = hi.conj().T @ ei

        eiThi = ei.conj().T @ hi
        vari = sigma2 / (2 * hi_norm)
        vari = max(vari, np.finfo(float).eps)
        mui_plus = vari * (np.real(eiThi + hiTei.T) / sigma2 - 1 / a)

        Kplus = (np.sqrt(vari * np.pi / 2)) * (np.sqrt(2 * vari * np.pi)) * (1 / a) * np.exp(mui_plus**2 / (2 * vari)) * (1 - norm.cdf(-mui_plus / np.sqrt(vari)))

        K = Kplus
        bet = 1 / K
        # print(f'Shape bet {bet.shape}')

        wstar = 1 / (bet / w + 1 - bet)
        # print(wstar)
        try:
            choix1 = np.random.binomial(1, wstar)
        except:
            choix1 = 0
            
        X[i] = 0
        Z[i] = 0
        # print(f'Choix 1 : {choix1}')
        if choix1 == 1:
            # Sample from the truncated normal distribution
            X[i] = rtnorm(0, np.inf, mui_plus, np.sqrt(vari))
            Z[i] = 1

    return X, Z


def modelSingleVoigt(frqppm, ppmref, sfrq, t_axis, amp, phs, llw, glw):
    frq = (frqppm - ppmref) * sfrq
    lambda_val = llw * np.pi
    gamma = glw
    
    # Generate Lorentzian peak in the time domain
    peak = amp * np.exp(
        (1j * 2 * np.pi * frq) * t_axis +
        (1j * phs / 180 * np.pi) +
        (-lambda_val * t_axis) +
        (-(gamma * t_axis)**2)
    )
    
    return peak


def SNR(s, s0):
    # Reshape matrices to vectors
    s = np.reshape(s, (-1, 1))
    s0 = np.reshape(s0, (-1, 1))
    
    # Calculate SNR in dB
    snr = 20 * np.log10(np.linalg.norm(s0, 'fro') / np.linalg.norm(s - s0, 'fro'))
    
    return snr



def MCMC_ber_laplace_MH_within_Gibbs(Signal, gamma0, H0, Observation, Nit, burn, t, grps_info, first, last):
    
    alphaw0 = 1.01
    alphaw1 = 1.01
    a_sigma2 = 1e-4
    b_sigma2 = 1e-4
    a_a = 0.001
    b_a = 0.001

    Pop, Mop = H0.shape
    try:
        Nl, Nc = Signal.shape
        Nlob, Ncob = Observation.shape
    except: 
        Nl = Signal.shape
        Nlob = Observation.shape
        Nc = 1
        Ncob = 1
    
    P = Nlob * Ncob
    M = Nl * Nc
    M = M[0]
    P = P[0]
    
    VSignal = Signal.flatten()
    VObservation = Observation.flatten()
    Chain_a = np.zeros(Nit)
    Chain_sigma2 = np.zeros(Nit)
    Chain_w = np.zeros(Nit)
    Chain_TSignal = np.zeros((M, Nit))
    TSignal = np.zeros((M, Nit - burn))
    TSignal_MAP = np.zeros((M, Nit - burn))
    TH = np.zeros((P, M, Nit - burn), dtype=complex)
    TZ = np.zeros((M, Nit - burn))
    Tsigma2 = np.zeros(Nit - burn)
    Ta = np.zeros(Nit - burn)
    Tw = np.zeros(Nit - burn)
    Nx = 1
    Chain_Signal = np.zeros(M)

    if grps_info == 0 : #'combine_all'
        acc_chain = np.zeros(Nit - burn)
        Chain_gamma = np.zeros(Nit)
        Chain_sigma2m = np.zeros(Nit)
        Chain_epsilon = np.zeros(Nit)
        Chain_phi0 = np.zeros(Nit)
        Chain_phi1 = np.zeros(Nit)
    else:
        acc_chain = np.zeros((Nit - burn, M))

    H = compute_H(H0, gamma0, grps_info, t, 0, 0, 0, 0)
    gamma = gamma0
    acc, rej = 0, 0
    sigma2m = 0
    epsilon = 0
    phi0 = 0
    phi1 = 0

    for ni in range(Nit):
        coeff1 = np.sum(VSignal != 0) + a_a
        coeff2 = b_a + np.linalg.norm(VSignal, 1)
        a = 1 / gamma_dist.rvs(coeff1, scale=1 / coeff2)
        Chain_a[ni] = a

        w = sample_w(VSignal, alphaw0, alphaw1)
        Chain_w[ni] = w

        c1 = a_sigma2 + P
        error = Observation - np.dot(H, VSignal)
        c2 = b_sigma2 + np.linalg.norm(error.flatten())**2
        sigma2 = 1 / (gamma_dist.rvs(c1, scale=1 / c2) + np.finfo(float).eps)
        Chain_sigma2[ni] = sigma2

        H = compute_H(H0, gamma, grps_info, t, sigma2m, epsilon, phi0, phi1)

        gamma, accept_result, acc, rej, _ = sample_gamma_MH(Observation, VSignal, sigma2, H0, H, gamma, grps_info, t, acc, rej, sigma2m, epsilon, phi0, phi1, first, last)
        Chain_gamma[ni] = gamma
        H = compute_H(H0, gamma, grps_info, t, sigma2m, epsilon, phi0, phi1)

        VSignal, VZ = sample_x_l1_Cplx_Operator(VSignal, a, w, sigma2, VObservation[first: last], H[first: last, :])
        Chain_TSignal[:, ni] = VSignal

        if ni > burn:
            TSignal[:, Nx] = VSignal
            TH[:, :, Nx] = H
            Tsigma2[Nx] = sigma2
            TZ[:, Nx] = VZ
            Ta[Nx] = a
            Tw[Nx] = w
            Chain_Signal = ((Nx - 1) * Chain_Signal + VSignal) / Nx
            Signal_MAP = map_sparse(TSignal[:, :Nx], TZ[:, :Nx])
            TSignal_MAP[:, Nx] = Signal_MAP
            acc_chain[Nx] = accept_result
            Nx += 1

    Signal = Signal_MAP
    sigma2 = np.mean(Tsigma2)
    a = np.mean(Ta)
    w = np.mean(Tw)
    gamma = np.mean(Chain_gamma)

    return Signal, gamma, Tsigma2, Ta, Tw, TSignal, TSignal_MAP, a, TZ, w, Chain_gamma, Chain_TSignal, Chain_sigma2m, Chain_phi0, Chain_phi1, Chain_epsilon



def FID2Spec(FID_t) :
    return  np.fft.fftshift(np.fft.fft(FID_t, axis=0))


def forward(params, t, Basis_fid, M, data, first, last):
    t = t[:, np.newaxis] 
    return FID2Spec((Basis_fid * np.exp(-t * params[M:M*2])) @ params[:M])[:, np.newaxis]


# def grad(params, t, Basis_fid, M, data, first, last):
#     t = t[:, np.newaxis]
#     con = params[:M]
#     gamma = params[M:2*M]

#     Fmet = FID2Spec((Basis_fid * np.exp(-t * params[M:M*2]))) #* params[:M])
#     Ftmetc = FID2Spec((t * Basis_fid * np.exp(-t * params[M:M*2])) * params[:M])
#     S = FID2Spec((Basis_fid * np.exp(-t * params[M:M*2])) @ params[:M])[:, np.newaxis]
#     # Gradients
#     dSdc = Fmet
#     dSdgamma = (-Ftmetc)

#     dS = np.concatenate((dSdc, dSdgamma), axis=1)
#     S = S[first: last]
#     dS = dS[first: last, :]
#     Spec = data[first: last, None]
#     grad = np.real(np.sum(S * np.conj(dS) + np.conj(S) * dS - np.conj(Spec) * dS - Spec * np.conj(dS), axis=0))
#     return grad

# Define objective function
def objective_function(params, t, Basis_fid, M, data, first, last):
    S = forward(params, t, Basis_fid, M, data, first, last)
    err = (data[first: last, None] - S[first: last]) #first: last
    sse = np.real(np.sum(err * np.conj(err)))
    return sse

def grad(params, t, Basis_fid, M, data, first, last):
    """
    returns gradient vector
    """
    m = Basis_fid
    n = m.shape[1]    # get number of basis functions
    con = params[:M]
    gamma = params[M:2*M]
    sigma = 0
    g = 1
    # Start
    E = np.zeros((m.shape[0], g), dtype=complex)
    

    for gg in range(g):
        # E[:, gg] = np.exp(-(1j * eps[gg] + gamma[gg] + t * sigma[gg]**2) * t).flatten() #WL 
        E[:, gg] = np.exp(-(gamma[gg]) * t).flatten()

    e_term = np.zeros(m.shape, dtype=complex)
    c = np.zeros((con.size, g))



    for i in range(n):
        e_term[:, i] = E[:, 0]
        c[i, gg] = con[i]
    m_term = m * e_term
    
    phi_term = np.exp(-1j * (0 + 0 * t[:, np.newaxis])) 
    Fmet = FID2Spec(m_term)
    Ftmet = FID2Spec(t[:, np.newaxis] * m_term)
    Ftmetc = Ftmet @ c
    Fmetcon = Fmet @ con[:, None]

    Spec = data[first:last, None]

    # Forward model
    S = (Fmetcon)


    # Gradients
    dSdc = phi_term * Fmet #WL
    dSdgamma = phi_term * (-Ftmetc)


    # Only compute within a range
    S = S[first:last]
    dSdc = dSdc[first:last, :]
    dSdgamma = dSdgamma[first:last, :] #WL
    
    dS = np.concatenate((dSdc, dSdgamma), axis=1)
    grad = np.real(np.sum(S * np.conj(dS) + np.conj(S) * dS - np.conj(Spec) * dS - Spec * np.conj(dS), axis=0))

    return grad



def l0_norm(vector):
    return np.count_nonzero(vector)


# MSE
def MSE(ground_truth, estimations):
    # Calculate the squared error
    squared_error = np.square(ground_truth - estimations)
    
    # Calculate the mean squared error
    mse = np.mean(squared_error, axis=-1)
    
    return mse
