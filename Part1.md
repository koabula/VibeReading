
# Part I

# Introduction and Classical Cryptography

# Introduction

# 1.1 Cryptography and Modern Cryptography

The Concise Oxford English Dictionary defines cryptography as “the art of writing or solving codes.” This is historically accurate, but does not capture the current breadth of the field or its present-day scientific foundations. The definition focuses solely on the codes that have been used for centuries to enable secret communication. But cryptography nowadays encompasses much more than this: it deals with mechanisms for ensuring integrity, techniques for exchanging secret keys, protocols for authenticating users, electronic auctions and elections, digital cash, and more. Without attempting to provide a complete characterization, we would say that modern cryptography involves the study of mathematical techniques for securing digital information, systems, and distributed computations against adversarial attacks. 

The dictionary definition also refers to cryptography as an art. Until late in the 20th century cryptography was, indeed, largely an art. Constructing good codes, or breaking existing ones, relied on creativity and a developed sense of how codes work. There was little theory to rely on and, for a long time, no working definition of what constitutes a good code. Beginning in the 1970s and 1980s, this picture of cryptography radically changed. A rich theory began to emerge, enabling the rigorous study of cryptography as a science and a mathematical discipline. This perspective has, in turn, influenced how researchers think about the broader field of computer security. 

Another very important difference between classical cryptography (say, before the 1980s) and modern cryptography relates to its adoption. Historically, the major consumers of cryptography were military organizations and governments. Today, cryptography is everywhere! If you have ever authenticated yourself by typing a password, purchased something by credit card over the Internet, or downloaded a verified update for your operating system, you have undoubtedly used cryptography. And, more and more, programmers with relatively little experience are being asked to “secure” the applications they write by incorporating cryptographic mechanisms. 

In short, cryptography has gone from a heuristic set of tools concerned with ensuring secret communication for the military to a science that helps secure systems for ordinary people all across the globe. This also means that cryptography has become a more central topic within computer science. 

Goals of this book. Our goal is to make the basic principles of modern cryptography accessible to students of computer science, electrical engineering, or mathematics; to professionals who want to incorporate cryptography in systems or software they are developing; and to anyone with a basic level of mathematical maturity who is interested in understanding this fascinating field. After completing this book, the reader should appreciate the security guarantees common cryptographic primitives are intended to provide; be aware of standard (secure) constructions of such primitives; and be able to perform a basic evaluation of new schemes based on their proofs of security (or lack thereof) and the mathematical assumptions underlying those proofs. It is not our intention for readers to become experts—or to be able to design new cryptosystems—after finishing this book, but we have attempted to provide the terminology and foundational material needed for the interested reader to subsequently study more advanced references in the area. 

This chapter. The focus of this book is the formal study of modern cryptography, but we begin in this chapter with a more informal discussion of “classical” cryptography. Besides allowing us to ease into the material, our treatment in this chapter will also serve to motivate the more rigorous approach we will be taking in the rest of the book. Our intention here is not to be exhaustive and, as such, this chapter should not be taken as a representative historical account. The reader interested in the history of cryptography is invited to consult the references at the end of this chapter. 

# 1.2 The Setting of Private-Key Encryption

Classical cryptography was concerned with designing and using codes (also called ciphers) that enable two parties to communicate secretly in the presence of an eavesdropper who can monitor all communication between them. In modern parlance, codes are called encryption schemes and that is the terminology we will use here. Security of all classical encryption schemes relied on a secret—a key—shared by the communicating parties in advance and unknown to the eavesdropper. This scenario is known as the private-key (or shared-/secret-key) setting, and private-key encryption is just one example of a cryptographic primitive used in this setting. Before describing some historical encryption schemes, we discuss private-key encryption more generally. 

In the setting of private-key encryption, two parties share a key and use this key when they want to communicate secretly. One party can send a message, or plaintext, to the other by using the shared key to encrypt (or “scramble”) the message and thus obtain a ciphertext that is transmitted to the receiver. The receiver uses the same key to decrypt (or “unscramble”) the ciphertext and recover the original message. Note the same key is used to convert the 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/e5b0f326-5081-4f30-b861-672a5e39020d/0fd3d424096bb74d5de0e0e275fb67fc238d2b0e12117c349ccdffc6d766872d.jpg)



FIGURE 1.1: One common setting of private-key cryptography (here, encryption): two parties share a key that they use to communicate securely.


plaintext into a ciphertext and back; that is why this is also known as the symmetric-key setting, where the symmetry lies in the fact that both parties hold the same key that is used for encryption and decryption. This is in contrast to asymmetric, or public-key, encryption (introduced in Chapter 10), where encryption and decryption use different keys. 

As already noted, the goal of encryption is to keep the plaintext hidden from an eavesdropper who can monitor the communication channel and observe the ciphertext. We discuss this in more detail later in this chapter, and spend a great deal of time in Chapters 2 and 3 formally defining this goal. 

There are two canonical applications of private-key cryptography. In the first, there are two distinct parties separated in space, e.g., a worker in New York communicating with her colleague in California; see Figure 1.2. These two users are assumed to have been able to securely share a key in advance of their communication. (Note that if one party simply sends the key to the other over the public communication channel, then the eavesdropper obtains the key too!) Often this is easy to accomplish by having the parties physically meet in a secure location to share a key before they separate; in the example just given, the co-workers might arrange to share a key when they are both in the New York office. In other cases, sharing a key securely is more difficult. For the next several chapters we simply assume that sharing a key is possible; we will revisit this issue in Chapter 10. 

The second widespread application of private-key cryptography involves the same party communicating with itself over time. (See Figure 1.2.) Consider, e.g., disk encryption, where a user encrypts some plaintext and stores the resulting ciphertext on their hard drive; the same user will return at a later 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/e5b0f326-5081-4f30-b861-672a5e39020d/bc66b191c8148cd1b6655d45b119bbf3e441673e576a714f7f858c284b513af6.jpg)



FIGURE 1.2: Another common setting of private-key cryptography (again, encryption): a single user stores data securely over time.


point in time to decrypt the ciphertext and recover the original data. The hard drive here serves as the communication channel on which an attacker might eavesdrop by gaining access to the hard drive and reading its contents. “Sharing” the key is now trivial, though the user still needs a secure and reliable way to remember/store the key for use at a later point in time. 

The syntax of encryption. Formally, a private-key encryption scheme is defined by specifying a message space $\mathcal { M }$ along with three algorithms: a procedure for generating keys (Gen), a procedure for encrypting (Enc), and a procedure for decrypting (Dec). The message space $\mathcal { M }$ defines the set of “legal” messages, i.e., those supported by the scheme. The algorithms have the following functionality: 

1. The key-generation algorithm Gen is a probabilistic algorithm that outputs a key $k$ chosen according to some distribution. 

2. The encryption algorithm Enc takes as input a key $k$ and a message $m$ and outputs a ciphertext $c$ . We denote by $\mathsf { E n c } _ { k } ( m )$ the encryption of the plaintext $m$ using the key $k$ . 

3. The decryption algorithm Dec takes as input a key $k$ and a ciphertext $c$ and outputs a plaintext $m$ . We denote the decryption of the ciphertext $c$ e using the key $k$ by $\mathsf { D e c } _ { k } ( c )$ . 

An encryption scheme must satisfy the following correctness requirement: for every key $k$ output by Gen and every message $m \in \mathcal { M }$ , it holds that 

$$
\operatorname {D e c} _ {k} \left(\operatorname {E n c} _ {k} (m)\right) = m.
$$

In words: encrypting a message and then decrypting the resulting ciphertext (using the same key) yields the original message. 

The set of all possible keys output by the key-generation algorithm is called the key space and is denoted by $\kappa$ . Almost always, Gen simply chooses a uniform key from the key space; in fact, one can assume without loss of generality that this is the case (see Exercise 2.1). 

Reviewing our earlier discussion, an encryption scheme can be used by two parties who wish to communicate as follows. First, Gen is run to obtain a key $k$ that the parties share. Later, when one party wants to send a plaintext $m$ to the other, she computes $c : = \mathsf { E n c } _ { k } ( m )$ and sends the resulting ciphertext $c$ over the public channel to the other party.1 Upon receiving $c$ , the other party computes $m : = { \mathsf { D e c } } _ { k } ( c )$ to recover the original plaintext. 

Keys and Kerckhoffs’ principle. As is clear from the above, if an eavesdropping adversary knows the algorithm Dec as well as the key $k$ shared by the two communicating parties, then that adversary will be able to decrypt any ciphertexts transmitted by those parties. It is for this reason that the communicating parties must share the key $k$ securely and keep $k$ completely secret from everyone else. Perhaps they should keep the decryption algorithm Dec secret, too? For that matter, might it not be better for them to keep all the details of the encryption scheme secret? 

In the late 19th century, Auguste Kerckhoffs argued the opposite in a paper he wrote elucidating several design principles for military ciphers. One of the most important of these, now known simply as Kerckhoffs’ principle, was: 

The cipher method must not be required to be secret, and it must be able to fall into the hands of the enemy without inconvenience. 

That is, an encryption scheme should be designed to be secure even if an eavesdropper knows all the details of the scheme, so long as the attacker doesn’t know the key being used. Stated differently, security should not rely on the encryption scheme being secret; instead, Kerckhoffs’ principle demands that security rely solely on secrecy of the key. 

There are three primary arguments in favor of Kerckhoffs’ principle. The first is that it is significantly easier for the parties to maintain secrecy of a short key than to keep secret the (more complicated) algorithm they are using. This is especially true if we imagine using encryption to secure the communication between all pairs of employees in some organization. Unless each pair of parties uses their own, unique algorithm, some parties will know the algorithm used by others. Information about the encryption algorithm might be leaked by one of these employees (say, after being fired), or obtained by an attacker using reverse engineering. In short, it is simply unrealistic to assume that the encryption algorithm will remain secret. 

Second, in case the honest parties’ shared, secret information is ever exposed, it will be much easier for them to change a key than to replace an encryption scheme. (Consider updating a file versus installing a new program.) Moreover, it is relatively trivial to generate a new random secret, whereas it would be a huge undertaking to design a new encryption scheme. 

Finally, for large-scale deployment it is significantly easier for users to all rely on the same encryption algorithm/software (with different keys) than for everyone to use their own custom algorithm. (This is true even for a single user who is communicating with several different parties.) In fact, it is desirable for encryption schemes to be standardized so that (1) compatibility is ensured by default and (2) users will utilize an encryption scheme that has undergone public scrutiny and in which no weaknesses have been found. 

Nowadays Kerckhoffs’ principle is understood as advocating that cryptographic designs be made completely public, in stark contrast to the notion of “security by obscurity” which suggests that keeping algorithms secret improves security. It is very dangerous to use a proprietary, “home-brewed” algorithm (i.e., a non-standardized algorithm designed in secret by some company). In contrast, published designs undergo public review and are therefore likely to be stronger. Many years of experience have demonstrated that it is very difficult to construct good cryptographic schemes. Therefore, our confidence in the security of a scheme is much higher if it has been extensively studied (by experts other than the designers of the scheme) and no weaknesses have been found. As simple and obvious as it may sound, the principle of open cryptographic design (i.e., Kerckhoffs’ principle) has been ignored over and over again with disastrous results. Fortunately, today there are enough secure, standardized, and widely available cryptosystems that there is no reason to use anything else. 

# 1.3 Historical Ciphers and Their Cryptanalysis

In our study of “classical” cryptography we will examine some historical encryption schemes and show that they are insecure. Our main aims in presenting this material are (1) to highlight the weaknesses of an “ad hoc” approach to cryptography, and thus motivate the modern, rigorous approach that will be taken in the rest of the book, and (2) to demonstrate that simple approaches to achieving secure encryption are unlikely to succeed. Along the way, we will present some central principles of cryptography inspired by the weaknesses of these historical schemes. 

In this section, plaintext characters are written in lower case and ciphertext characters are written in UPPER CASE for typographical clarity. 

Caesar’s cipher. One of the oldest recorded ciphers, known as Caesar’s 

cipher, is described in De Vita Caesarum, Divus Iulius (“The Lives of the Caesars, the Deified Julius”), written in approximately 110 CE: 

There are also letters of his to Cicero, as well as to his intimates on private affairs, and in the latter, if he had anything confidential to say, he wrote it in cipher, that is, by so changing the order of the letters of the alphabet, that not a word could be made out. . . 

Julius Caesar encrypted by shifting the letters of the alphabet 3 places forward: a was replaced with D, b with E, and so on. At the very end of the alphabet, the letters wrap around and so z was replaced with C, y with B, and x with A. For example, encryption of the message begin the attack now, with spaces removed, gives: 

# EHJLQWKHDWWDFNQRZ.

An immediate problem with this cipher is that the encryption method is fixed; there is no key. Thus, anyone learning how Caesar encrypted his messages would be able to decrypt effortlessly. 

Interestingly, a variant of this cipher called ROT-13 (where the shift is 13 places instead of 3) is still used nowadays in various online forums. It is understood that this does not provide any cryptographic security; it is used merely to ensure that the text (say, a movie spoiler) is unintelligible unless the reader of a message consciously chooses to decrypt it. 

The shift cipher and the sufficient key-space principle. The shift cipher can be viewed as a keyed variant of Caesar’s cipher.2 Specifically, in the shift cipher the key $k$ is a number between 0 and 25. To encrypt, letters are shifted as in Caesar’s cipher, but now by $k$ places. Mapping this to the syntax of encryption described earlier, the message space consists of arbitrary length strings of English letters with punctuation, spaces, and numerals removed, and with no distinction between upper and lower case. Algorithm Gen outputs a uniform key $k \in \{ 0 , \ldots , 2 5 \}$ ; algorithm Enc takes a key $k$ and a plaintext and shifts each letter of the plaintext forward $k$ positions (wrapping around at the end of the alphabet); and algorithm Dec takes a key $k$ and a ciphertext and shifts every letter of the ciphertext backward $k$ positions. 

A more mathematical description is obtained by equating the English alphabet with the set $\{ 0 , \ldots , 2 5 \}$ (so $\mathsf { a } = 0$ , $\mathtt { b } = 1$ , etc.). The message space $\mathcal { M }$ is then any finite sequence of integers from this set. Encryption of the message $r n = m _ { 1 } \cdot \cdot \cdot m _ { \ell }$ (where $m _ { i } \in \{ 0 , \ldots , 2 5 \} _ { }$ ) using key $k$ is given by 

$$
\operatorname {E n c} _ {k} \left(m _ {1} \dots m _ {\ell}\right) = c _ {1} \dots c _ {\ell}, \quad \text {w h e r e} c _ {i} = \left[ \left(m _ {i} + k\right) \bmod 2 6 \right].
$$

(The notation $[ a \mathrm { m o d } N ]$ denotes the remainder of $a$ upon division by $N$ , with $0 \leq [ a \mathrm { m o d } N ] < N$ . We refer to the process mapping $a$ to $[ a \mathrm { m o d } N ]$ 

as reduction modulo $N$ ; we will have more to say about this beginning in Chapter 8.) Decryption of a ciphertext $c = c _ { 1 } \cdot \cdot \cdot c _ { \ell }$ using key $k$ is given by 

$$
\operatorname {D e c} _ {k} \left(c _ {1} \dots c _ {\ell}\right) = m _ {1} \dots m _ {\ell}, \quad \text {w h e r e} m _ {i} = \left[ \left(c _ {i} - k\right) \bmod 2 6 \right].
$$

Is the shift cipher secure? Before reading on, try to decrypt the following ciphertext that was generated using the shift cipher and a secret key $k$ : 

# OVDTHUFWVZZPISLRLFZHYLAOLYL.

Is it possible to recover the message without knowing $k$ ? Actually, it is trivial! The reason is that there are only 26 possible keys. So one can try to decrypt the ciphertext using every possible key and thereby obtain a list of 26 candidate plaintexts. The correct plaintext will certainly be on this list; moreover, if the ciphertext is “long enough” then the correct plaintext will likely be the only candidate on the list that “makes sense.” (The latter is not necessarily true, but will be true most of the time. Even when it is not, the attack narrows down the set of potential plaintexts to at most 26 possibilities.) By scanning the list of candidates it is easy to recover the original plaintext. 

An attack that involves trying every possible key is called a brute-force or exhaustive-search attack. Clearly, for an encryption scheme to be secure it must not be vulnerable to such an attack.3 This observation is known as the sufficient key-space principle: 

Any secure encryption scheme must have a key space that is sufficiently large to make an exhaustive-search attack infeasible. 

One can debate what amount of effort makes a task “infeasible,” and an exact determination of feasibility depends on both the resources of a potential attacker and the length of time the sender and receiver want to ensure secrecy of their communication. Nowadays, attackers can use supercomputers, tens of thousands of personal computers, or graphics processing units (GPUs) to speed up brute-force attacks. To protect against such attacks the key space must therefore be very large—say, of size at least $2 ^ { 7 0 }$ , and even larger if one is concerned about long-term security against a well-funded attacker. 

The sufficient key-space principle gives a necessary condition for security, but not a sufficient one. The next example demonstrates this. 

The mono-alphabetic substitution cipher. In the shift cipher, the key defines a map from each letter of the (plaintext) alphabet to some letter of the (ciphertext) alphabet, where the map is a fixed shift determined by the key. In the mono-alphabetic substitution cipher, the key also defines a map on the alphabet, but the map is now allowed to be arbitrary subject only to the constraint that it be one-to-one so that decryption is possible. The key 

space thus consists of all bijections, or permutations, of the alphabet. So, for example, the key that defines the following permutation 

<table><tr><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td><td>g</td><td>h</td><td>i</td><td>j</td><td>k</td><td>l</td><td>m</td><td>n</td><td>o</td><td>p</td><td>q</td><td>r</td><td>s</td><td>t</td><td>u</td><td>v</td><td>w</td><td>x</td><td>y</td><td>z</td></tr><tr><td>X</td><td>E</td><td>U</td><td>A</td><td>D</td><td>N</td><td>B</td><td>K</td><td>V</td><td>M</td><td>R</td><td>O</td><td>C</td><td>Q</td><td>F</td><td>S</td><td>Y</td><td>H</td><td>W</td><td>G</td><td>L</td><td>Z</td><td>I</td><td>J</td><td>P</td><td>T</td></tr></table>

(in which a maps to ${ \tt X }$ , etc.) would encrypt the message tellhimaboutme to GDOOKVCXEFLGCD. The name of this cipher comes from the fact that the key defines a (fixed) substitution for individual characters of the plaintext. 

Assuming the English alphabet is being used, the key space is of size $2 6 ! =$ $2 6 \cdot 2 5 \cdot 2 4 \cdot \cdot \cdot 2 \cdot 1$ , or approximately $2 ^ { 8 8 }$ , and a brute-force attack is infeasible. This, however, does not mean the cipher is secure! In fact, as we will show next, it is easy to break this scheme even though it has a large key space. 

Assume English-language text is being encrypted (i.e., the text is grammatically correct English writing, not just text written using characters of the English alphabet). The mono-alphabetic substitution cipher can then be attacked by utilizing statistical patterns of the English language. (Of course, the same attack works for any language.) The attack relies on the facts that: 

1. For any key, the mapping of each letter is fixed, and so if $\ominus$ is mapped to D, then every appearance of $\ominus$ in the plaintext will result in the appearance of D in the ciphertext. 

2. The frequency distribution of individual letters in the English language is known (see Figure 1.3). Of course, very short texts may deviate from this distribution, but even texts consisting of only a few sentences tend to have distributions that are very close to the average. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/e5b0f326-5081-4f30-b861-672a5e39020d/f80083b24886d5fad98cb06d2ac49d3b8f6bf0f484885323d1d0e011dc17e1ed.jpg)



FIGURE 1.3: Average letter frequencies for English-language text.


The attack works by tabulating the frequency distribution of characters in the ciphertext, i.e., recording that A appeared 11 times, B appeared 4 times, and so on. These frequencies are then compared to the known letter frequencies of normal English text. One can then guess parts of the mapping defined by the key based on the observed frequencies. For example, since $\ominus$ is the most frequent letter in English, one can guess that the most frequent character in the ciphertext corresponds to the plaintext character $\ominus$ , and so on. Some of the guesses may be wrong, but enough of the guesses will be correct to enable relatively quick decryption (especially utilizing other knowledge of English, such as the fact that u generally follows q, and that h is likely to appear between $^ \texttt { t }$ and $\bowtie$ ). We conclude that although the mono-alphabetic substitution cipher has a large key space, it is still insecure. 

It should not be surprising that the mono-alphabetic substitution cipher can be quickly broken, since puzzles based on this cipher appear in newspapers (and are solved by some people before their morning coffee!). We recommend that you try to decipher the following ciphertext—this should convince you how easy the attack is to carry out. (Use Figure 1.3 to help you.) 

JGRMQOYGHMVBJWRWQFPWHGFFDQGFPFZRKBEEBJIZQQOCIBZKLFAFGQVFZFWWE OGWOPFGFHWOLPHLRLOLFDMFGQWBLWBWQOLKFWBYLBLYLFSFLJGRMQBOLWJVFP FWQVHQWFFPQOQVFPQOCFPOGFWFJIGFQVHLHLROQVFGWJVFPFOLFHGQVQVFILE OGQILHQFQGIQVVOSFAFGBWQVHQWIJVWJVFPFWHGFIWIHZZRQGBABHZQOCGFHX 

An improved attack on the shift cipher. We can use letter-frequency tables to give an improved attack on the shift cipher. Our previous attack on the shift cipher required decrypting the ciphertext using each possible key, and then checking which key results in a plaintext that “makes sense.” A drawback of this approach is that it is somewhat difficult to automate, since it is difficult for a computer to check whether a given plaintext “makes sense.” (We do not claim that it would be impossible, as the attack could be automated using a dictionary of valid English words. We only claim that it would not be trivial to automate.) Moreover, there may be cases—we will see one later—where the plaintext characters are distributed just like English-language text even though the plaintext itself is not valid English, in which case checking for a plaintext that “makes sense” will not work. 

We now describe an attack that does not suffer from these drawbacks. As before, associate the letters of the English alphabet with $0 , \ldots , 2 5$ . Let $p _ { i }$ , with $0 \leq p _ { i } \leq 1$ , denote the frequency of the $i$ th letter in normal English text (ignoring spaces, punctuation, etc.). Calculation using Figure 1.3 gives 

$$
\sum_ {i = 0} ^ {2 5} p _ {i} ^ {2} \approx 0. 0 6 5. \tag {1.1}
$$

Now, say we are given some ciphertext and let $q _ { i }$ denote the frequency of the $_ i$ th letter of the alphabet in this ciphertext; i.e., $q _ { i }$ is simply the number 

of occurrences of the $i$ th letter of the alphabet in the ciphertext divided by the length of the ciphertext. If the key is $k$ , then $p _ { i }$ should be roughly equal to $q _ { i + k }$ for all $i$ , because the $i$ th letter is mapped to the $( i + k ) \mathrm { t h }$ letter. (We use $i + k$ instead of the more cumbersome $\displaystyle { \lfloor i + k }$ mod 26].) Thus, if we compute 

$$
I _ {j} \stackrel {\mathrm {d e f}} {=} \sum_ {i = 0} ^ {2 5} p _ {i} \cdot q _ {i + j}
$$

for each value of $j \in \{ 0 , \ldots , 2 5 \}$ , then we expect to find that $I _ { k } \approx 0 . 0 6 5$ (where $k$ is the actual key), whereas $I _ { j }$ for $j \neq k$ will be different from 0.065. This leads to a key-recovery attack that is easy to automate: compute $I _ { j }$ for all $j$ , and then output the value $k$ for which $I _ { k }$ is closest to 0.065. 

The Vigen`ere (poly-alphabetic shift) cipher. The statistical attack on the mono-alphabetic substitution cipher can be carried out because the key defines a fixed mapping that is applied letter-by-letter to the plaintext. Such an attack could be thwarted by using a poly-alphabetic substitution cipher where the key instead defines a mapping that is applied on blocks of plaintext characters. Here, for example, a key might map the 2-character block ab to DZ while mapping ac to TY; note that the plaintext character a does not get mapped to a fixed ciphertext character. Poly-alphabetic substitution ciphers “smooth out” the frequency distribution of characters in the ciphertext and make it harder to perform statistical analysis. 

The Vigen`ere cipher, a special case of the above also called the polyalphabetic shift cipher, works by applying several independent instances of the shift cipher in sequence. The key is now viewed as a string of letters; encryption is done by shifting each plaintext character by the amount indicated by the next character of the key, wrapping around in the key when necessary. (This degenerates to the shift cipher if the key has length 1.) For example, encryption of the message tellhimaboutme using the key cafe would work as follows: 

<table><tr><td>Plaintext:</td><td>tellhimaboutme</td></tr><tr><td>Key (repeated):</td><td>cafecafecafeca</td></tr><tr><td>Ciphertext:</td><td>VEQPJIREDOZXOE</td></tr></table>

(The key need not be an English word.) This is exactly the same as encrypting the first, fifth, ninth, . . . characters with the shift cipher and key c; the second, sixth, tenth, . . . characters with key a; the third, seventh, . . . characters with f; and the fourth, eighth, . . . characters with $\ominus$ . Notice that in the above example l is mapped once to $\mathsf { U }$ and once to P. Furthermore, the ciphertext character E is sometimes obtained from $\ominus$ and sometimes from a. Thus, the character frequencies of the ciphertext are “smoothed out,” as desired. 

If the key is sufficiently long, cracking this cipher appears daunting. Indeed, it had been considered by many to be “unbreakable,” and although it was invented in the 16th century, a systematic attack on the scheme was only devised hundreds of years later. 

Attacking the Vigen`ere cipher. A first observation in attacking the Vigen`ere cipher is that if the length of the key is known then attacking the cipher is relatively easy. Specifically, say the length of the key, also called the period, is $t$ . Write the key $k$ as $k = k _ { 1 } \cdot \cdot \cdot k _ { t }$ where each $k _ { i }$ is a letter of the alphabet. An observed ciphertext $c = c _ { 1 } c _ { 2 } \cdots$ can be divided into $t$ parts where each part can be viewed as having been encrypted using a shift cipher. Specifically, for all $j \in \{ 1 , \ldots , t \}$ the ciphertext characters 

$$
c _ {j}, c _ {j + t}, c _ {j + 2 t}, \dots
$$

all resulted by shifting the corresponding characters of the plaintext by $k _ { j }$ positions. We refer to the above sequence of characters as the $j$ th stream. All that remains is to determine, for each of the $t$ streams, which of the 26 possible shifts was used. This is not as trivial as in the case of the shift cipher, because it is no longer possible to simply try different shifts in an attempt to determine when decryption of a stream “makes sense.” (Recall that a stream does not correspond to consecutive letters of the plaintext.) Furthermore, trying to guess the entire key $k$ at once would require a bruteforce search through $2 6 ^ { t }$ different possibilities, which is infeasible for large $t$ . Nevertheless, we can still use letter-frequency analysis to analyze each stream independently. Namely, for each stream we tabulate the frequency of each ciphertext character and then check which of the 26 possible shifts yields the “right” probability distribution for that stream. Since this can be carried out independently for each stream (i.e., for each character of the key), this attack takes time $2 6 \cdot t$ rather than time $2 6 ^ { t }$ . 

A more principled, easier-to-automate approach is to use the improved method for attacking the shift cipher discussed earlier. That attack did not rely on checking for a plaintext that “made sense,” but only relied on the underlying frequency distribution of characters in the plaintext. 

Either of the above approaches gives a successful attack when the key length is known. What if the key length is unknown? 

Note first that as long as the maximum length $T$ of the key is not too large, we can simply repeat the above attack $T$ times (for each possible value $t \in \{ 1 , \ldots , T \} ,$ ). This leads to at most $T$ different candidate plaintexts, among which the true plaintext will likely be easy to identify. So an unknown key length is not a serious obstacle. 

There are also more efficient ways to determine the key length from an observed ciphertext. One is to use Kasiski’s method, published in the mid-19th century. The first step here is to identify repeated patterns of length 2 or 3 in the ciphertext. These are likely the result of certain bigrams or trigrams that appear frequently in the plaintext. For example, consider the common word “the.” This word will be mapped to different ciphertext characters, depending on its position in the plaintext. However, if it appears twice in the same relative position, then it will be mapped to the same ciphertext characters. For a sufficiently long plaintext, there is thus a good chance that “the” will be mapped repeatedly to the same ciphertext characters. 

Consider the following concrete example with the key beads (spaces have been added for clarity): 

<table><tr><td>Plaintext:</td><td>the man and the woman retrieved the letter from the post office</td></tr><tr><td>Key:</td><td>bea dsb ead sbe adsbe adsbeadsb ead sbeads bead sbe adsb eadsb</td></tr><tr><td>Ciphertext:</td><td>ULE PSO ENG LII WREBR RHLSMEYWE XHH DFXTHJ GVOP LII PRKU SFIADI</td></tr></table>

The word the is mapped sometimes to ULE, sometimes to LII, and sometimes to XHH. However, it is mapped twice to LII, and in a long enough text it is likely that it would be mapped multiple times to each of these possibilities. Kasiski’s observation was that the distance between such repeated appearances (assuming they are not coincidental) must be a multiple of the period. (In the above example, the period is 5 and the distance between the two appearances of LII is 30, which is 6 times the period.) Therefore, the greatest common divisor of the distances between repeated sequences (assuming they are not coincidental) will yield the key length $t$ or a multiple thereof. 

An alternative approach, called the index of coincidence method, is more methodical and hence easier to automate. Recall that if the key length is $t$ , then the ciphertext characters 

$$
c _ {1}, c _ {1 + t}, c _ {1 + 2 t}, \dots
$$

in the first stream all resulted from encryption using the same shift. This means that the frequencies of the characters in this sequence are expected to be identical to the character frequencies of standard English text in some shifted order. In more detail: let $q _ { i }$ denote the observed frequency of the $_ i$ th English letter in this stream; this is simply the number of occurrences of the $i$ th letter of the alphabet divided by the total number of letters in the stream. If the shift used here is $j$ (i.e., if the first character $k _ { 1 }$ of the key is equal to $j$ ), then for all $_ i$ we expect $q _ { i + j } \approx p _ { i }$ , where $p _ { i }$ is the frequency of the $_ i$ th letter of the alphabet in standard English text. (Once again, we use $q _ { i + j }$ in place of $q _ { [ i + j }$ mod 26].) But this means that the sequence $q _ { 0 } , \ldots , q _ { 2 5 }$ is just the sequence $p _ { 0 } , \ldots , p _ { 2 5 }$ shifted $j$ places. As a consequence (cf. Equation (1.1)): 

$$
\sum_ {i = 0} ^ {2 5} q _ {i} ^ {2} \approx \sum_ {i = 0} ^ {2 5} p _ {i} ^ {2} \approx 0. 0 6 5.
$$

This leads to a nice way to determine the key length $t$ . For $\tau = 1 , 2 , \dots$ , look at the sequence of ciphertext characters $c _ { 1 } , c _ { 1 + \tau } , c _ { 1 + 2 \tau } , . . . .$ and tabulate $q _ { 0 } , \ldots , q _ { 2 5 }$ for this sequence. Then compute 

$$
S _ {\tau} \stackrel {{\mathrm {d e f}}} {{=}} \sum_ {i = 0} ^ {2 5} q _ {i} ^ {2}.
$$

When $\tau = t$ we expect $S _ { \tau } \approx 0 . 0 6 5$ , as discussed above. On the other hand, if $\tau$ is not a multiple of $t$ we expect that all characters will occur with roughly equal 

probability in the sequence $c _ { 1 } , c _ { 1 + \tau } , c _ { 1 + 2 \tau } , . . . .$ , and so we expect $q _ { i } \approx 1 / 2 6$ for all $i$ . In this case we will obtain 

$$
S _ {\tau} \approx \sum_ {i = 0} ^ {2 5} \left(\frac {1}{2 6}\right) ^ {2} \approx 0. 0 3 8.
$$

The smallest value of $\tau$ for which $S _ { \tau } \approx 0 . 0 6 5$ is thus likely the key length. One can further validate a guess $\tau$ by carrying out a similar calculation using the second stream $c _ { 2 } , c _ { 2 + \tau } , c _ { 2 + 2 \tau } , . . .$ , etc. 

Ciphertext length and cryptanalytic attacks. The above attacks on the Vigen`ere cipher require a longer ciphertext than the attacks on previous schemes. For example, the index of coincidence method requires $c _ { 1 } , c _ { 1 + t } , c _ { 1 + 2 t }$ (where $t$ is the actual key length) to be sufficiently long in order to ensure that the observed frequencies match what is expected; the ciphertext itself must then be roughly $t$ times larger. Similarly, the attack we showed on the monoalphabetic substitution cipher requires a longer ciphertext than the attack on the shift cipher (which can work for encryptions of even a single word). This illustrates that a longer key can, in general, require the cryptanalyst to obtain more ciphertext in order to carry out an attack. (Indeed, the Vigen`ere cipher can be shown to be secure if the key is as long as what is being encrypted. We will see a similar phenomenon in the next chapter.) 

Conclusions. We have presented only a few historical ciphers. Beyond their historical interest, our aim in presenting them was to illustrate some important lessons. Perhaps the most important is that designing secure ciphers is hard. The Vigen`ere cipher remained unbroken for a long time. Far more complex schemes have also been used. But a complex scheme is not necessarily secure, and all historical schemes have been broken. 

# 1.4 Principles of Modern Cryptography

As should be clear from the previous section, cryptography was historically more of an art than a science. Schemes were designed in an ad hoc manner and evaluated based on their perceived complexity or cleverness. A scheme would be analyzed to see if any attacks could be found; if so, the scheme would be “patched” to thwart that attack, and the process repeated. Although there may have been agreement that some schemes were not secure (as evidenced by an especially damaging attack), there was no agreed-upon notion of what requirements a “secure” scheme should satisfy, and no way to give evidence that any specific scheme was secure. 

Over the past several decades, cryptography has developed into more of a science. Schemes are now developed and analyzed in a more systematic 

manner, with the ultimate goal being to give a rigorous proof that a given construction is secure. In order to articulate such proofs, we first need formal definitions that pin down exactly what “secure” means; such definitions are useful and interesting in their own right. As it turns out, most cryptographic proofs rely on currently unproven assumptions about the algorithmic hardness of certain mathematical problems; any such assumptions must be made explicit and be stated precisely. An emphasis on definitions, assumptions, and proofs distinguishes modern cryptography from classical cryptography; we discuss these three principles in greater detail in the following sections. 

# 1.4.1 Principle 1 – Formal Definitions

One of the key contributions of modern cryptography has been the recognition that formal definitions of security are essential for the proper design, study, evaluation, and usage of cryptographic primitives. Put bluntly: 

If you don’t understand what you want to achieve, how can you possibly know when (or if ) you have achieved it? 

Formal definitions provide such understanding by giving a clear description of what threats are in scope and what security guarantees are desired. As such, definitions can help guide the design of cryptographic schemes. Indeed, it is much better to formalize what is required before the design process begins, rather than to come up with a definition post facto once the design is complete. The latter approach risks having the design phase end when the designers’ patience is exhausted (rather than when the goal has been met), or may result in a construction achieving more than is needed at the expense of efficiency. 

Definitions also offer a way to evaluate and analyze what is constructed. With a definition in place, one can study a proposed scheme to see if it achieves the desired guarantees; in some cases, one can even prove a given construction secure (see Section 1.4.3) by showing that it meets the definition. On the flip side, definitions can be used to conclusively show that a given scheme is not secure, insofar as the scheme does not satisfy the definition. In particular, note that the attacks in the previous section do not automatically demonstrate that any of the schemes shown there is “insecure.” For example, the attack on the Vigen`ere cipher assumed that sufficiently long English text was being encrypted, but could the Vigen`ere cipher be “secure” if short English text, or compressed text (which will have roughly uniform letter frequencies), is encrypted? It is hard to say without a formal definition in place. 

Definitions enable a meaningful comparison of schemes. As we will see, there can be multiple (valid) ways to define security; the “right” one depends on the context in which a scheme is used. A scheme satisfying a weaker definition may be more efficient than another scheme satisfying a stronger definition; with precise definitions we can properly evaluate the trade-offs between the two schemes. Along the same lines, definitions enable secure usage of schemes. Consider the question of deciding which encryption scheme 

to use for some larger application. A sound way to approach the problem is to first understand what notion of security is required for that application, and then find an encryption scheme satisfying that notion. A side benefit of this approach is modularity: a designer can “swap out” one encryption scheme and replace it with another (that also satisfies the necessary definition of security) without having to worry about affecting security of the overall application. 

Writing a formal definition forces one to think about what is essential to the problem at hand and what properties are extraneous. Going through the process often reveals subtleties of the problem that were not obvious at first glance. We illustrate this next for the case of encryption. 

An example: secure encryption. A common mistake is to think that formal definitions are not needed, or are trivial to come up with, because “everyone has an intuitive idea of what security means.” This is not the case. As an example, we consider the case of encryption. (The reader may want to pause here to think about how they would formally define what it means for an encryption scheme to be secure.) Although we postpone a formal definition of secure encryption to the next two chapters, we describe here informally what such a definition should capture. 

In general, a security definition has two components: a security guarantee (or, from the attacker’s point of view, what constitutes a successful attack on the scheme) and a threat model. The security guarantee defines what the scheme is intended to prevent the attacker from doing, while the threat model describes the power of the adversary, i.e., what actions the attacker is assumed able to carry out. 

Let’s start with the first of these. What should a secure encryption scheme guarantee? Here are some thoughts: 

It should be impossible for an attacker to recover the key. We have previously observed that if an attacker can determine the key shared by two parties using some scheme, then that scheme cannot be secure. However, it is easy to come up with schemes for which key recovery is impossible, yet the scheme is blatantly insecure. Consider, e.g., the scheme where $\mathsf { E n c } _ { k } ( m ) = m$ . The ciphertext leaks no information about the key (and so the key cannot be recovered if it is long enough) yet the message is sent in the clear! We thus see that inability to recover the key is not sufficient for security. This makes sense: the aim of encryption is to protect the message; the key is a means for achieving this but is, in itself, unimportant. 

It should be impossible for an attacker to recover the entire plaintext from the ciphertext. This definition is better, but is still far from satisfactory. In particular, this definition would consider an encryption scheme secure if its ciphertexts revealed 90% of the plaintext, as long as 10% of the plaintext remained hard to figure out. This is clearly unacceptable in most common applications of encryption; for example, when encrypting 

a salary database, we would be justifiably upset if 90% of employees’ salaries were revealed! 

It should be impossible for an attacker to recover any character of the plaintext from the ciphertext. This looks like a good definition, yet is still not sufficient. Going back to the example of encrypting a salary database, we would not consider an encryption scheme secure if it reveals whether an employee’s salary is more than or less than $\$ 100,000$ , even if it does not reveal any particular digit of that employee’s salary. Similarly, we would not want an encryption scheme to reveal whether employee $A$ makes more than employee $B$ . 

Another issue is how to formalize what it means for an adversary to “recover a character of the plaintext.” What if an attacker correctly guesses, through sheer luck or external information, that the least significant digit of someone’s salary is 0? Clearly that should not render an encryption scheme insecure, and so any viable definition must somehow rule out such behavior as being a successful attack. 

• The “right” answer: regardless of any information an attacker already has, a ciphertext should leak no additional information about the underlying plaintext. This informal definition captures all the concerns outlined above. Note in particular that it does not try to define what information about the plaintext is “meaningful”; it simply requires that no information be leaked. This is important, as it means that a secure encryption scheme is suitable for all potential applications in which secrecy is required. 

What is missing here is a precise, mathematical formulation of the definition. How should we capture an attacker’s prior knowledge about the plaintext? And what does it mean to (not) leak information? We will return to these questions in the next two chapters; see especially Definitions 2.3 and 3.12. 

Now that we have fixed a security goal, it remains to specify a threat model. This specifies what “power” the attacker is assumed to have, but does not place any restrictions on the adversary’s strategy. This is an important distinction: we specify what we assume about the adversary’s abilities, but we do not assume anything about how it uses those abilities. It is impossible to foresee what strategies might be used in an attack, and history has proven that attempts to do so are doomed to failure. 

There are several plausible options for the threat model in the context of encryption; standard ones, in order of increasing power of the attacker, are: 

Ciphertext-only attack: This is the most basic attack, and refers to a scenario where the adversary just observes a ciphertext (or multiple ciphertexts) and attempts to determine information about the underlying plaintext (or plaintexts). This is the threat model we have been 

implicitly assuming when discussing classical encryption schemes in the previous section. 

• Known-plaintext attack: Here, the adversary is able to learn one or more plaintext/ciphertext pairs generated using some key. The aim of the adversary is then to deduce information about the underlying plaintext of some other ciphertext produced using the same key. 

All the classical encryption schemes we have seen are trivial to break using a known-plaintext attack; we leave a demonstration as an exercise. 

• Chosen-plaintext attack: In this attack, the adversary can obtain plaintext/ciphertext pairs (as above) for plaintexts of its choice. 

Chosen-ciphertext attack: The final type of attack is one where the adversary is additionally able to obtain (some information about) the decryption of ciphertexts of its choice, e.g., whether the decryption of some ciphertext chosen by the attacker yields a valid English message. The adversary’s aim, once again, is to learn information about the underlying plaintext of some other ciphertext (whose decryption the adversary is unable to obtain directly). 

None of these threat models is inherently better than any other; the right one to use depends on the environment in which an encryption scheme is deployed. 

The first two types of attack are the easiest to carry out. In a ciphertextonly attack, the only thing the adversary needs to do is eavesdrop on the public communication channel over which encrypted messages are sent. In a known-plaintext attack it is assumed that the adversary somehow also obtains ciphertexts corresponding to known plaintexts. This is often easy to accomplish because not all encrypted messages are confidential, at least not indefinitely. As a trivial example, two parties may always encrypt a “hello” message whenever they begin communicating. As a more complex example, encryption may be used to keep quarterly-earnings reports secret until their release date; in this case, anyone eavesdropping on the ciphertext will later obtain the corresponding plaintext. 

In the latter two attacks the adversary is assumed to be able to obtain encryptions and/or decryptions of plaintexts/ciphertexts of its choice. This may at first seem strange, and we defer a more detailed discussion of these attacks, and their practicality, to Section 3.4.2 (for chosen-plaintext attacks) and Section 3.7 (for chosen-ciphertext attacks). 

# 1.4.2 Principle 2 – Precise Assumptions

Most modern cryptographic constructions cannot be proven secure unconditionally; such proofs would require resolving questions in the theory of computational complexity that seem far from being answered today. The result of 

this unfortunate state of affairs is that proofs of security typically rely on assumptions. Modern cryptography requires any such assumptions to be made explicit and mathematically precise. At the most basic level, this is simply because mathematical proofs of security require this. But there are other reasons as well: 

1. Validation of assumptions: By their very nature, assumptions are statements that are not proven but are instead conjectured to be true. In order to strengthen our belief in some assumption, it is necessary for the assumption to be studied. The more the assumption is examined and tested without being refuted, the more confident we are that the assumption is true. Furthermore, study of an assumption can provide evidence of its validity by showing that it is implied by some other assumption that is also widely believed. 

If the assumption being relied upon is not precisely stated, it cannot be studied and (potentially) refuted. Thus, a pre-condition to increasing our confidence in an assumption is having a precise statement of what exactly is being assumed. 

2. Comparison of schemes: Often in cryptography we are presented with two schemes that can both be proven to satisfy some definition, each based on a different assumption. Assuming all else is equal, which scheme should be preferred? If the assumption on which the first scheme is based is weaker than the assumption on which the second scheme is based (i.e., the second assumption implies the first), then the first scheme is preferable since it may turn out that the second assumption is false while the first assumption is true. If the assumptions used by the two schemes are not comparable, then the general rule is to prefer the scheme that is based on the better-studied assumption in which there is greater confidence. 

3. Understanding the necessary assumptions: An encryption scheme may be based on some underlying building block. If some weaknesses are later found in the building block, how can we tell whether the encryption scheme is still secure? If the underlying assumptions regarding the building block are made clear as part of proving security of the scheme, then we need only check whether the required assumptions are affected by the new weaknesses that were found. 

A question that sometimes arises is: rather than prove a scheme secure based on some other assumption, why not simply assume that the construction itself is secure? In some cases—e.g., when a scheme has successfully resisted attack for many years—this may be a reasonable approach. But this approach is never preferred, and is downright dangerous when a new scheme is being introduced. The reasons above help explain why. First, an assumption that has been tested for several years is preferable to a new, ad hoc assumption 

that is introduced along with a new construction. Second, there is a general preference for assumptions that are simpler to state, since such assumptions are easier to study and to (potentially) refute. So, for example, an assumption that some mathematical problem is hard to solve is simpler to study and evaluate than the assumption that an encryption scheme satisfies a complex security definition. Another advantage of relying on “lower-level” assumptions (rather than just assuming a construction is secure) is that these low-level assumptions can typically be used in other constructions. Finally, low-level assumptions can provide modularity. Consider an encryption scheme whose security relies on some assumed property of one of its building blocks. If the underlying building block turns out not to satisfy the stated assumption, the encryption scheme can still be instantiated using a different component that is believed to satisfy the necessary requirements. 

# 1.4.3 Principle 3 – Proofs of Security

The two principles described above allow us to achieve our goal of providing a rigorous proof that a construction satisfies a given definition under certain specified assumptions. Such proofs are especially important in the context of cryptography where there is an attacker who is actively trying to “break” some scheme. Proofs of security give an iron-clad guarantee—relative to the definition and assumptions—that no attacker will succeed; this is much better than taking an unprincipled or heuristic approach to the problem. Without a proof that no adversary with the specified resources can break some scheme, we are left only with our intuition that this is the case. Experience has shown that intuition in cryptography and computer security is disastrous. There are countless examples of unproven schemes that were broken, sometimes immediately and sometimes years after being developed. 

# Summary: Rigorous vs. Ad Hoc Approaches to Security

Reliance on definitions, assumptions, and proofs constitutes a rigorous approach to cryptography that is distinct from the informal approach of classical cryptography. Unfortunately, unprincipled, “off-the-cuff” solutions are still designed and deployed by those wishing to obtain a quick solution to a problem, or by those who are simply unknowledgable. We hope this book will contribute to an awareness of the rigorous approach and its importance in developing provably secure schemes. 

# 1.4.4 Provable Security and Real-World Security

Much of modern cryptography now rests on sound mathematical foundations. But this does not mean that the field is no longer partly an art as well. The rigorous approach leaves room for creativity in developing definitions suited to contemporary applications and environments, in proposing new 

mathematical assumptions or designing new primitives, and in constructing novel schemes and proving them secure. There will also, of course, always be the art of attacking deployed cryptosystems, even if they are proven secure. We expand on this point next. 

The approach taken by modern cryptography has revolutionized the field, and helps provide confidence in the security of cryptographic schemes deployed in the real world. But it is important not to overstate what a proof of security implies. A proof of security is always relative to the definition being considered and the assumption(s) being used. If the security guarantee does not match what is needed, or the threat model does not capture the adversary’s true abilities, then the proof may be irrelevant. Similarly, if the assumption that is relied upon turns out to be false, then the proof of security is meaningless. 

The take-away point is that provable security of a scheme does not necessarily imply security of that scheme in the real world.4 While some have viewed this as a drawback of provable security, we view this optimistically as illustrating the strength of the approach. To attack a provably secure scheme in the real world, it suffices to focus attention on the definition (i.e., to explore how the idealized definition differs from the real-world environment in which the scheme is deployed) or the underlying assumptions (i.e., to see whether they hold). In turn, it is the job of cryptographers to continually refine their definitions to more closely match the real world, and to investigate their assumptions to test their validity. Provable security does not end the age-old battle between attacker and defender, but it does provide a framework that helps shift the odds in the defender’s favor. 

# References and Additional Reading

In this chapter, we have studied just a few of the known historical ciphers. There are many others of both historical and mathematical interest, and we refer the reader to textbooks by Stinson [168] or Trappe and Washington [169] for further details. The important role cryptography has played throughout history is a fascinating subject covered in books by Kahn [97] and Singh [163]. 

Kerckhoffs’ principles were elucidated in [103, 104]. Shannon [154] was the first to pursue a rigorous approach to cryptography based on precise definitions and mathematical proofs; we explore his work in the next chapter. 

# Exercises

1.1 Decrypt the ciphertext provided at the end of the section on monoalphabetic substitution ciphers. 

1.2 Provide a formal definition of the Gen, Enc, and Dec algorithms for the mono-alphabetic substitution cipher. 

1.3 Provide a formal definition of the Gen, Enc, and Dec algorithms for the Vigen`ere cipher. (Note: there are several plausible choices for Gen; choose one.) 

1.4 Implement the attacks described in this chapter for the shift cipher and the Vigen`ere cipher. 

1.5 Show that the shift, substitution, and Vigen`ere ciphers are all trivial to break using a chosen-plaintext attack. How much chosen plaintext is needed to recover the key for each of the ciphers? 

1.6 Assume an attacker knows that a user’s password is either abcd or bedg. Say the user encrypts his password using the shift cipher, and the attacker sees the resulting ciphertext. Show how the attacker can determine the user’s password, or explain why this is not possible. 

1.7 Repeat the previous exercise for the Vigen`ere cipher using period 2, using period 3, and using period 4. 

1.8 The shift, substitution, and Vigen`ere ciphers can also be defined over the 128-character ASCII alphabet (rather than the 26-character English alphabet). 

(a) Provide a formal definition of each of these schemes in this case. 

(b) Discuss how the attacks we have shown in this chapter can be modified to break each of these modified schemes. 

# Perfectly Secret Encryption

In the previous chapter we presented historical encryption schemes and showed how they can be broken with little computational effort. In this chapter, we look at the other extreme and study encryption schemes that are provably secure even against an adversary with unbounded computational power. Such schemes are called perfectly secret. Besides rigorously defining the notion, we will explore conditions under which perfect secrecy can be achieved. (Beginning in this chapter, we assume familiarity with basic probability theory. The relevant notions are reviewed in Appendix A.3.) 

The material in this chapter belongs, in some sense, more to the world of “classical” cryptography than to the world of “modern” cryptography. Besides the fact that all the material introduced here was developed before the revolution in cryptography that took place in the mid-1970s and 1980s, the constructions we study in this chapter rely only on the first and third principles outlined in Section 1.4. That is, precise mathematical definitions are used and rigorous proofs are given, but it will not be necessary to rely on any unproven computational assumptions. It is clearly advantageous to avoid such assumptions; we will see, however, that doing so has inherent limitations. Thus, in addition to serving as a good basis for understanding the principles underlying modern cryptography, the results of this chapter also justify our later adoption of all three of the aforementioned principles. 

Beginning with this chapter, we will define security and analyze schemes using probabilistic experiments involving algorithms making randomized choices; a basic example is given by communicating parties’ choosing a random key. Thus, before returning to the subject of cryptography per se, we briefly discuss the issue of generating randomness suitable for cryptographic applications. 

Generating randomness. Throughout the book, we will simply assume that parties have access to an unlimited supply of independent, unbiased random bits. In practice, where do these random bits come from? In principle, one could generate a small number of random bits by hand, e.g., by flipping a fair coin. But such an approach is not very convenient, nor does it scale. 

Modern random-number generation proceeds in two steps. First, a “pool” of high-entropy data is collected. (For our purposes a formal definition of entropy is not needed, and it suffices to think of entropy as a measure of unpredictability.) Next, this high-entropy data is processed to yield a sequence of nearly independent and unbiased bits. This second step is necessary since high-entropy data is not necessarily uniform. 

For the first step, some source of unpredictable data is needed. There are several ways such data can be acquired. One technique is to rely on external inputs, for example, delays between network events, hard-disk access times, keystrokes or mouse movements made by the user, and so on. Such data is likely to be far from uniform, but if enough measurements are taken the resulting pool of data is expected to have sufficient entropy. More sophisticated approaches—which, by design, incorporate random-number generation more tightly into the system at the hardware level—have also been used. These rely on physical phenomena such as thermal/shot noise or radioactive decay. Intel has recently developed a processor that includes a digital random-number generator on the processor chip and provides a dedicated instruction for accessing the resulting random bits (after they have been suitably processed to yield independent, unbiased bits, as discussed next). 

The processing needed to “smooth” the high-entropy data to obtain (nearly) uniform bits is a non-trivial one, and is discussed briefly in Section 5.6.4. Here, we just give a simple example to give an idea of what is done. Imagine that our high-entropy pool results from a sequence of biased coin flips, where “heads” occurs with probability $p$ and “tails” with probability $1 - p$ . (We do assume, however, that the result of any coin flip is independent of all other coin flips. In practice this assumption is typically not valid.) The result of 1,000 such coin flips certainly has high entropy, but is not close to uniform. We can obtain a uniform distribution by considering the coin flips in pairs: if we see a head followed by a tail then we output “0,” and if we see a tail followed by a head then we output “1.” (If we see two heads or two tails in a row, we output nothing, and simply move on to the next pair.) The probability that any pair results in a “ $0$ ” is $p \cdot ( 1 - p )$ , which is exactly equal to the probability that any pair results in a “1,” and we thus obtain a uniformly distributed output from our initial high-entropy pool. 

Care must be taken in how random bits are produced, and using poor random-number generators can often leave a good cryptosystem vulnerable to attack. One should use a random-number generator that is designed for cryptographic use, rather than a “general-purpose” random-number generator, which is not suitable for cryptographic applications. In particular, the rand() function in the C stdlib.h library is not cryptographically secure, and using it in cryptographic settings can have disastrous consequences. 

# 2.1 Definitions

We begin by recalling and expanding upon the syntax that was introduced in the previous chapter. An encryption scheme is defined by three algorithms Gen, Enc, and Dec, as well as a specification of a (finite) message space $\mathcal { M }$ 

with $| \mathcal { M } | > 1$ .1 The key-generation algorithm Gen is a probabilistic algorithm that outputs a key $k$ chosen according to some distribution. We denote by $\kappa$ the (finite) key space, i.e., the set of all possible keys that can be output by Gen. The encryption algorithm Enc takes as input a key $k \in \mathcal { K }$ and a message $m \in \mathcal { M }$ , and outputs a ciphertext $c$ . We now allow the encryption algorithm to be probabilistic (so $\mathsf { E n c } _ { k } ( m )$ might output a different ciphertext when run multiple times), and we write $c \gets \mathsf { E n c } _ { k } ( m )$ to denote the possibly probabilistic process by which message $m$ is encrypted using key $k$ to give ciphertext $c$ . (In case Enc is deterministic, we may emphasize this by writing $c : = \mathtt { E n c } _ { k } ( m )$ . Looking ahead, we also sometimes use the notation $x \gets S$ to denote uniform selection of $x$ from a set $S$ .) We let $\mathcal { C }$ denote the set of all possible ciphertexts that can be output by $\mathsf { E n c } _ { k } ( m )$ , for all possible choices of $k \in \mathcal { K }$ and $m \in \mathcal { M }$ (and for all random choices of Enc in case it is randomized). The decryption algorithm Dec takes as input a key $k \in \mathcal { K }$ and a ciphertext $c \in { \mathcal { C } }$ and outputs a message $m \in \mathcal { M }$ . We assume perfect correctness, meaning that for all $k \in \mathcal { K }$ , $m \in \mathcal { M }$ , and any ciphertext $c$ output by $\mathsf { E n c } _ { k } ( m )$ , it holds that ${ \mathsf { D e c } } _ { k } ( c ) = m$ with probability 1. Perfect correctness implies that we may assume Dec is deterministic without loss of generality, since $\mathsf { D e c } _ { k } ( c )$ must give the same output every time it is run. We will thus write $m : = { \mathsf { D e c } } _ { k } ( c )$ to denote the process of decrypting ciphertext $c$ using key $k$ to yield the message $m$ . 

In the definitions and theorems below, we refer to probability distributions over $\kappa$ , $\mathcal { M }$ , and $c$ . The distribution over $\kappa$ is the one defined by running Gen and taking the output. (It is almost always the case that Gen chooses a key uniformly from $\mathcal { K }$ and, in fact, we may assume this without loss of generality; see Exercise 2.1.) We let $K$ be a random variable denoting the value of the key output by Gen; thus, for any $k \in \mathcal { K }$ , $\operatorname* { P r } [ K = k ]$ denotes the probability that the key output by Gen is equal to $k$ . Similarly, we let $M$ be a random variable denoting the message being encrypted, so $\operatorname* { P r } [ M = m ]$ denotes the probability that the message takes on the value $m \in \mathcal { M }$ . The probability distribution of the message is not determined by the encryption scheme itself, but instead reflects the likelihood of different messages being sent by the parties using the scheme, as well as an adversary’s uncertainty about what will be sent. As an example, an adversary may know that the message will either be attack today or don’t attack. The adversary may even know (by other means) that with probability 0.7 the message will be a command to attack and with probability 0.3 the message will be a command not to attack. In this case, we have $\operatorname* { P r } [ M = \tt { a t t a c k \ t o d a y } ] = 0 . 7$ and $\operatorname* { P r } [ M = { \tt d o n } ^ { \prime } \tt t$ $\operatorname* { P r } [ M = \mathtt { d o n } ^ { \prime } \mathtt { t a t t a c k } ] = 0 . 3$ . 

$K$ and $M$ are assumed to be independent, i.e., what is being communicated by the parties is independent of the key they happen to share. This makes sense, among other reasons, because the distribution over $\kappa$ is determined by 

the encryption scheme itself (since it is defined by Gen), while the distribution over $\mathcal { M }$ depends on the context in which the encryption scheme is being used. 

Fixing an encryption scheme and a distribution over $\mathcal { M }$ determines a distribution over the space of ciphertexts $\boldsymbol { \mathscr { C } }$ given by choosing a key $k \in \mathcal { K }$ (according to Gen) and a message $m \in \mathcal { M }$ (according to the given distribution), and then computing the ciphertext $c \gets \mathsf { E n c } _ { k } ( m )$ . We let $C$ be the random variable denoting the resulting ciphertext and so, for $c \in { \mathcal { C } }$ , write $\mathrm { P r } [ C = c ]$ to denote the probability that the ciphertext is equal to the fixed value $c$ . 

# Example 2.1

We work through a simple example for the shift cipher (cf. Section 1.3). Here, by definition, we have $\mathcal { K } = \{ 0 , \ldots , 2 5 \}$ with $\operatorname* { P r } [ K = k ] = 1 / 2 6$ for each $k \in \kappa$ . 

Say we are given the following distribution over $\mathcal { M }$ : 

$$
\Pr [ M = \mathbf {a} ] = 0. 7 \quad \text {a n d} \quad \Pr [ M = \mathbf {z} ] = 0. 3.
$$

What is the probability that the ciphertext is B? There are only two ways this can occur: either $M = \mathsf { a }$ and $K = 1$ , or $M = z$ and $K = 2$ . By independence of $M$ and $K$ , we have 

$$
\begin{array}{l} \Pr [ M = \mathsf {a} \wedge K = 1 ] = \Pr [ M = \mathsf {a} ] \cdot \Pr [ K = 1 ] \\ = 0. 7 \cdot \left(\frac {1}{2 6}\right). \\ \end{array}
$$

Similarly, $\operatorname* { P r } [ M = \mathbf { z } \wedge K = 2 ] = 0 . 3 \cdot \left( { \frac { 1 } { 2 6 } } \right)$ . Therefore, 

$$
\begin{array}{l} \operatorname * {P r} [ C = \mathsf {B} ] = \operatorname * {P r} [ M = \mathsf {a} \land K = 1 ] + \operatorname * {P r} [ M = \mathsf {z} \land K = 2 ] \\ = 0. 7 \cdot \left(\frac {1}{2 6}\right) + 0. 3 \cdot \left(\frac {1}{2 6}\right) = 1 / 2 6. \\ \end{array}
$$

We can calculate conditional probabilities as well. For example, what is the probability that the message a was encrypted, given that we observe ciphertext B? Using Bayes’ Theorem (Theorem A.8) we have 

$$
\begin{array}{l} \operatorname * {P r} [ M = \mathsf {a} \mid C = \mathsf {B} ] = \frac {\operatorname * {P r} [ C = \mathsf {B} \mid M = \mathsf {a} ] \cdot \operatorname * {P r} [ M = \mathsf {a} ]}{\operatorname * {P r} [ C = \mathsf {B} ]} \\ = \frac {0 . 7 \cdot \operatorname * {P r} [ C = \mathtt {B} \mid M = \mathtt {a} ]}{1 / 2 6}. \\ \end{array}
$$

Note that $\operatorname* { P r } [ C = { \tt B } \mid M = { \tt a } ] = 1 / 2 6$ , since if $M = \mathsf { a }$ then the only way $C = \mathtt { B }$ can occur is if $K = 1$ (which occurs with probability 1/26). We conclude that $\operatorname* { P r } [ M = \mathtt { a } \ | \ C = \mathtt { B } ] = 0 . 7$ . ♦ 

# Example 2.2

Consider the shift cipher again, but with the following distribution over $\mathcal { M }$ : 

$$
\Pr [ M = \operatorname {k i m} ] = 0. 5, \Pr [ M = \operatorname {a n n} ] = 0. 2, \Pr [ M = \operatorname {b o o} ] = 0. 3.
$$

What is the probability that $C = \mathsf { D Q Q } ?$ The only way this ciphertext can occur is if $M = \mathtt { a n n }$ and $K = 3$ , or $M = \mathtt { b o o }$ and $K = 2$ , which happens with probability $0 . 2 \cdot 1 / 2 6 + 0 . 3 \cdot 1 / 2 6 = 1 / 5 2$ . 

So what is the probability that ann was encrypted, conditioned on observing the ciphertext DQQ? A calculation as above using Bayes’ Theorem gives $\operatorname* { P r } [ M = { \tt a n n } \mid C = { \tt D Q Q } ] = 0 . 4$ . ♦ 

Perfect secrecy. We are now ready to define the notion of perfect secrecy. We imagine an adversary who knows the probability distribution over $\mathcal { M }$ ; that is, the adversary knows the likelihood that different messages will be sent. This adversary also knows the encryption scheme being used; the only thing unknown to the adversary is the key shared by the parties. A message is chosen by one of the honest parties and encrypted, and the resulting ciphertext transmitted to the other party. The adversary can eavesdrop on the parties’ communication, and thus observe this ciphertext. (That is, this is a ciphertext-only attack, where the attacker gets only a single ciphertext.) For a scheme to be perfectly secret, observing this ciphertext should have no effect on the adversary’s knowledge regarding the actual message that was sent; in other words, the a posteriori probability that some message $m \in \mathcal { M }$ was sent, conditioned on the ciphertext that was observed, should be no different from the a priori probability that $m$ would be sent. This means that the ciphertext reveals nothing about the underlying plaintext, and the adversary learns absolutely nothing about the plaintext that was encrypted. Formally: 

DEFINITION 2.3 An encryption scheme (Gen, Enc, Dec) with message space $\mathcal { M }$ is perfectly secret if for every probability distribution over $\mathcal { M }$ , every message $m \in \mathcal { M }$ , and every ciphertext $c \in { \mathcal { C } }$ for which $\mathrm { P r } [ C = c ] > 0$ : 

$$
\operatorname * {P r} [ M = m \mid C = c ] = \operatorname * {P r} [ M = m ].
$$

(The requirement that $\mathrm { P r } [ C = c ] > 0$ is a technical one needed to prevent conditioning on a zero-probability event.) 

We now give an equivalent formulation of perfect secrecy. Informally, this formulation requires that the probability distribution of the ciphertext does not depend on the plaintext, i.e., for any two messages $m , m ^ { \prime } \in \mathcal { M }$ the distribution of the ciphertext when $m$ is encrypted should be identical to the distribution of the ciphertext when $m ^ { \prime }$ is encrypted. Formally, for every $m , m ^ { \prime } \in \mathcal { M }$ , and every $c \in { \mathcal { C } }$ , 

$$
\Pr [ \mathsf {E n c} _ {K} (m) = c ] = \Pr [ \mathsf {E n c} _ {K} (m ^ {\prime}) = c ] \tag {2.1}
$$

(where the probabilities are over choice of $K$ and any randomness of Enc). This implies that the ciphertext contains no information about the plaintext, and that it is impossible to distinguish an encryption of $m$ from an encryption of $m ^ { \prime }$ , since the distributions over the ciphertext are the same in each case. 

LEMMA 2.4 An encryption scheme (Gen, Enc, Dec) with message space $\mathcal { M }$ is perfectly secret if and only if Equation (2.1) holds for every $m , m ^ { \prime } \in \mathcal { M }$ and every $c \in { \mathcal { C } }$ . 

PROOF We show that if the stated condition holds, then the scheme is perfectly secret; the converse implication is left to Exercise 2.4. Fix a distribution over $\mathcal { M }$ , a message $m$ , and a ciphertext $c$ for which $\mathrm { P r } [ C = c ] > 0$ . If $\operatorname* { P r } [ M = m ] = 0$ then we trivially have 

$$
\Pr [ M = m \mid C = c ] = 0 = \Pr [ M = m ].
$$

So, assume $\operatorname* { P r } [ M = m ] > 0$ . Notice first that 

$$
\Pr \left[ C = c \mid M = m \right] = \Pr \left[ \mathsf {E n c} _ {K} (M) = c \mid M = m \right] = \Pr \left[ \mathsf {E n c} _ {K} (m) = c \right],
$$

where the first equality is by definition of the random variable $C$ , and the second is because we condition on the event that $M$ is equal to $m$ . Set $\delta _ { c } \ { \stackrel { \mathrm { d e f } } { = } }$ $\operatorname* { P r } [ \mathsf { E n c } _ { K } ( m ) = c ] = \operatorname* { P r } [ C = c \mid M = m ]$ . If the condition of the lemma holds, then for every $m ^ { \prime } \in \mathcal { M }$ we have $\mathrm { P r } [ \mathsf { E n c } _ { K } ( m ^ { \prime } ) = c ] = \mathrm { P r } [ C = c \mid M = m ^ { \prime } ] = \delta _ { c }$ . Using Bayes’ Theorem (see Appendix A.3), we thus have 

$$
\begin{array}{l} \operatorname * {P r} [ M = m \mid C = c ] = \frac {\operatorname * {P r} [ C = c \mid M = m ] \cdot \operatorname * {P r} [ M = m ]}{\operatorname * {P r} [ C = c ]} \\ = \frac {\operatorname* {P r} [ C = c \mid M = m ] \cdot \operatorname* {P r} [ M = m ]}{\sum_ {m ^ {\prime} \in \mathcal {M}} \operatorname* {P r} [ C = c \mid M = m ^ {\prime} ] \cdot \operatorname* {P r} [ M = m ^ {\prime} ]} \\ = \frac {\delta_ {c} \cdot \Pr [ M = m ]}{\sum_ {m ^ {\prime} \in \mathcal {M}} \delta_ {c} \cdot \Pr [ M = m ^ {\prime} ]} \\ = \frac {\Pr [ M = m ]}{\sum_ {m ^ {\prime} \in \mathcal {M}} \Pr [ M = m ^ {\prime} ]} = \Pr [ M = m ], \\ \end{array}
$$

where the summation is over $m ^ { \prime } \in \mathcal { M }$ with $\operatorname* { P r } [ M = m ^ { \prime } ] \neq 0$ . We conclude that for every $m \in \mathcal { M }$ and $c \in { \mathcal { C } }$ for which $\mathrm { P r } [ C = c ] > 0$ , it holds that $\operatorname* { P r } [ M = m | C = c ] = \operatorname* { P r } [ M = m ]$ , and so the scheme is perfectly secret. 

Perfect (adversarial) indistinguishability. We conclude this section by presenting another equivalent definition of perfect secrecy. This definition is based on an experiment involving an adversary passively observing a ciphertext and then trying to guess which of two possible messages was encrypted. We introduce this notion since it will serve as our starting point for defining computational security in the next chapter. Indeed, throughout the rest of the book we will often use experiments of this sort to define security. 

In the present context, we consider the following experiment: an adversary $\boldsymbol { A }$ first specifies two arbitrary messages $m _ { 0 } , m _ { 1 } \in \mathcal { M }$ . One of these two 

messages is chosen uniformly at random and encrypted using a random key; the resulting ciphertext is given to $\mathcal { A }$ . Finally, $\boldsymbol { A }$ outputs a “guess” as to which of the two messages was encrypted; $\mathcal { A }$ succeeds if it guesses correctly. An encryption scheme is perfectly indistinguishable if no adversary $\mathcal { A }$ can succeed with probability better than $1 / 2$ . (Note that, for any encryption scheme, $\mathcal { A }$ can succeed with probability $1 / 2$ by outputting a uniform guess; the requirement is simply that no attacker can do any better than this.) We stress that no limitations are placed on the computational power of $\boldsymbol { A }$ . 

Formally, let $\Pi = ( \mathsf { G e n } , \mathsf { E n c } , \mathsf { D e c } )$ be an encryption scheme with message space $\mathcal { M }$ . Let $\mathcal { A }$ be an adversary, which is formally just a (stateful) algorithm. We define an experiment $\mathsf { P r i v } \mathsf { K } _ { \mathcal { A , \Pi } } ^ { \mathsf { e a v } }$ as follows: 

The adversarial indistinguishability experiment PrivK $\stackrel {  } { \mathcal { A } } , \stackrel { \quad } { \Pi }$ 

1. The adversary $\mathcal { A }$ outputs a pair of messages $m _ { 0 } , m _ { 1 } \in \mathcal { M }$ 

2. A key $k$ is generated using Gen, and a uniform bit $b \in \{ 0 , 1 \}$ is chosen. Ciphertext $c \gets \mathsf { E n c } _ { k } ( m _ { b } )$ is computed and given to A. We refer to c as the challenge ciphertext. 

3. A outputs a bit $b ^ { \prime }$ 

4. The output of the experiment is defined to be 1 if $\ b ^ { \prime } \ = \ b$ , and 0 otherwise. We write $\mathsf { P r i v } \mathsf { K } _ { \mathcal { A , \Pi } } ^ { \mathsf { e a v } } = 1$ if the output of the experiment is 1 and in this case we say that $\mathcal { A }$ succeeds. 

As noted earlier, it is trivial for $\mathcal { A }$ to succeed with probability 1/2 by outputting a random guess. Perfect indistinguishability requires that it is impossible for any $\mathcal { A }$ to do better. 

DEFINITION 2.5 Encryption scheme Π = (Gen, Enc, Dec) with message space $\mathcal { M }$ is perfectly indistinguishable if for every $\mathcal { A }$ it holds that 

$$
\Pr \left[ \mathsf {P r i v} K _ {\mathcal {A}, \Pi} ^ {\mathrm {e a v}} = 1 \right] = \frac {1}{2}.
$$

The following lemma states that Definition 2.5 is equivalent to Definition 2.3. We leave the proof of the lemma as Exercise 2.5. 

LEMMA 2.6 Encryption scheme Π is perfectly secret if and only if it is perfectly indistinguishable. 

# Example 2.7

We show that the Vigen`ere cipher is not perfectly indistinguishable, at least for certain parameters. Concretely, let $\mathrm { I I }$ denote the Vigen`ere cipher for the message space of two-character strings, and where the period is chosen uniformly in $\{ 1 , 2 \}$ . To show that $\mathrm { I I }$ is not perfectly indistinguishable, we exhibit {an adversary $\mathcal { A }$ for which $\begin{array} { r } { \operatorname* { P r } \left[ \mathsf { P r i v } \mathsf { K } _ { \mathcal { A , \Pi } } ^ { \mathsf { e a v } } = 1 \right] > \frac { 1 } { 2 } } \end{array}$ . 

Adversary $\mathcal { A }$ does: 

1. Output $m _ { 0 } = \mathtt { a a }$ and $m _ { 1 } = \mathsf { a b }$ . 

2. Upon receiving the challenge ciphertext $c = c _ { 1 } c _ { 2 }$ , do the following: if $c _ { 1 } = c _ { 2 }$ output 0; else output 1. 

Computation of $\operatorname* { P r } \left\lfloor \mathsf { P r i v K } _ { \mathcal { A , \Pi } } ^ { \mathsf { e a v } } = 1 \right\rfloor$ is tedious but straightforward. 

$$
\begin{array}{l} \Pr \left[ \operatorname {P r i v} K _ {\mathcal {A}, \Pi} ^ {\text {e a v}} = 1 \right] \\ = \frac {1}{2} \cdot \Pr \left[ \operatorname {P r i v} K _ {\mathcal {A}, \Pi} ^ {\text {e a v}} = 1 \mid b = 0 \right] + \frac {1}{2} \cdot \Pr \left[ \operatorname {P r i v} K _ {\mathcal {A}, \Pi} ^ {\text {e a v}} = 1 \mid b = 1 \right] \\ = \frac {1}{2} \cdot \Pr [ \mathcal {A} \text {o u t p u t s} 0 \mid b = 0 ] + \frac {1}{2} \cdot \Pr [ \mathcal {A} \text {o u t p u t s} 1 \mid b = 1 ], \tag {2.2} \\ \end{array}
$$

where $b$ is the uniform bit determining which message gets encrypted. $\mathcal { A }$ outputs 0 if and only if the two characters of the ciphertext $c = c _ { 1 } c _ { 2 }$ are equal. When $b = 0$ (so $m _ { 0 } = \mathtt { a a }$ is encrypted) then $c _ { 1 } = c _ { 2 }$ if either (1) a key of period 1 is chosen, or (2) a key of period 2 is chosen, and both characters of the key are equal. The former occurs with probability $\textstyle { \frac { 1 } { 2 } }$ , and the latter occurs with probability $\textstyle { \frac { 1 } { 2 } } \cdot { \frac { 1 } { 2 6 } }$ . So 

$$
\Pr \left[ \mathcal {A} \text {o u t p u t s} 0 \mid b = 0 \right] = \frac {1}{2} + \frac {1}{2} \cdot \frac {1}{2 6} \approx 0. 5 2.
$$

When $b = 1$ then $c _ { 1 } = c _ { 2 }$ only if a key of period 2 is chosen and the first character of the key is one more than the second character of the key, which happens with probability $\frac { 1 } { 2 } \cdot \frac { 1 } { 2 6 }$ . So 

$$
\operatorname * {P r} [ \mathcal {A} \text {o u t p u t s} 1 \mid b = 1 ] = 1 - \operatorname * {P r} [ \mathcal {A} \text {o u t p u t s} 0 \mid b = 1 ] = 1 - \frac {1}{2} \cdot \frac {1}{2 6} \approx 0. 9 8.
$$

Plugging into Equation (2.2) then gives 

$$
\operatorname * {P r} \left[ \mathsf {P r i v K} _ {\mathcal {A}, \Pi} ^ {\mathrm {e a v}} = 1 \right] = \frac {1}{2} \cdot \left(\frac {1}{2} + \frac {1}{2} \cdot \frac {1}{2 6} + 1 - \frac {1}{2} \cdot \frac {1}{2 6}\right) = 0. 7 5 > \frac {1}{2},
$$

and the scheme is not perfectly indistinguishable. 

# 2.2 The One-Time Pad

In 1917, Vernam patented a perfectly secret encryption scheme now called the one-time pad. At the time Vernam proposed the scheme, there was no proof that it was perfectly secret; in fact, there was not yet a notion of what perfect secrecy was. Approximately 25 years later, however, Shannon introduced the definition of perfect secrecy and demonstrated that the one-time pad achieves that level of security. 

# CONSTRUCTION 2.8

Fix an integer $\ell > 0$ . The message space $\mathcal { M }$ , key space $\kappa$ , and ciphertext space $c$ are all equal to $\{ 0 , 1 \} ^ { \ell }$ (the set of all binary strings of length $\ell$ ). 

• Gen: the key-generation algorithm chooses a key from ${ \mathcal K } = \{ 0 , 1 \} ^ { \ell }$ according to the uniform distribution (i.e., each of the $2 ^ { \ell }$ strings in the space is chosen as the key with probability exactly $2 ^ { - \ell }$ ). 

• Enc: given a key $k \in \{ 0 , 1 \} ^ { \ell }$ and a message $m \in \{ 0 , 1 \} ^ { \ell }$ , the encryption algorithm outputs the ciphertext $c : = k \oplus m$ . 

• Dec: given a key $k \in \{ 0 , 1 \} ^ { \ell }$ and a ciphertext $c \in \{ 0 , 1 \} ^ { \ell }$ , the decryption algorithm outputs the message $m : = k \oplus c$ . 

The one-time pad encryption scheme. 

In describing the scheme we let $a \oplus b$ denote the bitwise exclusive-or (XOR) of two binary strings $a$ and $b$ (i.e., if $a = a _ { 1 } \cdots a _ { \ell }$ and $b = b _ { 1 } \cdots b _ { \ell }$ are $\ell$ -bit strings, then $a \oplus b$ is the $\ell$ -bit string given by $a _ { 1 } \oplus b _ { 1 } \cdot \cdot \cdot a _ { \ell } \oplus b _ { \ell }$ ). In the onetime pad encryption scheme the key is a uniform string of the same length as the message; the ciphertext is computed by simply XORing the key and the message. A formal definition is given as Construction 2.8. Before discussing security, we first verify correctness: for every key $k$ and every message $m$ it holds that $\mathsf { D e c } _ { k } ( \mathsf { E n c } _ { k } ( m ) ) = k \oplus k \oplus m = m$ , and so the one-time pad constitutes a valid encryption scheme. 

One can easily prove perfect secrecy of the one-time pad using Lemma 2.4 and the fact that the ciphertext is uniformly distributed regardless of what message is encrypted. We give a proof based directly on the original definition. 

THEOREM 2.9 The one-time pad encryption scheme is perfectly secret. 

PROOF We first compute $\operatorname* { P r } [ C = c \mid M = m ^ { \prime } ]$ for arbitrary $c \in { \mathcal { C } }$ and $m ^ { \prime } \in \mathcal { M }$ . For the one-time pad, 

$$
\begin{array}{l} \Pr \left[ C = c \mid M = m ^ {\prime} \right] = \Pr \left[ \mathsf {E n c} _ {K} \left(m ^ {\prime}\right) = c \right] = \Pr \left[ m ^ {\prime} \oplus K = c \right] \\ = \Pr [ K = m ^ {\prime} \oplus c ] \\ = 2 ^ {- \ell}, \\ \end{array}
$$

where the final equality holds because the key $K$ is a uniform $\ell$ -bit string. Fix any distribution over $\mathcal { M }$ . For any $c \in { \mathcal { C } }$ , we have 

$$
\begin{array}{l} \Pr [ C = c ] = \sum_ {m ^ {\prime} \in \mathcal {M}} \Pr [ C = c \mid M = m ^ {\prime} ] \cdot \Pr [ M = m ^ {\prime} ] \\ = 2 ^ {- \ell} \cdot \sum_ {m ^ {\prime} \in \mathcal {M}} \Pr [ M = m ^ {\prime} ] \\ = 2 ^ {- \ell}, \\ \end{array}
$$

where the sum is over $m ^ { \prime } \in \mathcal { M }$ with $\operatorname* { P r } [ M = m ^ { \prime } ] \neq 0$ . Bayes’ Theorem gives: 

$$
\begin{array}{l} \Pr [ M = m \mid C = c ] = \frac {\Pr [ C = c \mid M = m ] \cdot \Pr [ M = m ]}{\Pr [ C = c ]} \\ = \frac {2 ^ {- \ell} \cdot \Pr [ M = m ]}{2 ^ {- \ell}} \\ = \Pr [ M = m ]. \\ \end{array}
$$

We conclude that the one-time pad is perfectly secret. 

The one-time pad was used by several national-intelligence agencies in the mid-20th century to encrypt sensitive traffic. Perhaps most famously, the “red phone” linking the White House and the Kremlin during the Cold War was protected using one-time pad encryption, where the governments of the US and USSR would exchange extremely long keys using trusted couriers carrying briefcases of paper on which random characters were written. 

Notwithstanding the above, one-time pad encryption is rarely used any more due to a number of drawbacks it has. Most prominent is that the key is as long as the message.2 This limits the usefulness of the scheme for sending very long messages (as it may be difficult to securely share and store a very long key), and is problematic when the parties cannot predict in advance (an upper bound on) how long the message will be. 

Moreover, the one-time pad—as the name indicates—is only secure if used once (with the same key). Although we did not yet define a notion of secrecy when multiple messages are encrypted, it is easy to see that encrypting more than one message with the same key leaks a lot of information. In particular, say two messages $m , m ^ { \prime }$ are encrypted using the same key $k$ . An adversary who obtains $c = m \oplus k$ and $c ^ { \prime } = m ^ { \prime } \oplus k$ can compute 

$$
c \oplus c ^ {\prime} = (m \oplus k) \oplus (m ^ {\prime} \oplus k) = m \oplus m ^ {\prime}
$$

and thus learn the exclusive-or of the two messages or, equivalently, exactly where the two messages differ. While this may not seem very significant, it is enough to rule out any claims of perfect secrecy for encrypting two messages using the same key. Moreover, if the messages correspond to natural-language text, then given the exclusive-or of two sufficiently long messages it is possible to perform frequency analysis (as in the previous chapter, though more complex) and recover the messages themselves. An interesting historical example of this is given by the VENONA project, as part of which the US and UK were able to decrypt ciphertexts sent by the Soviet Union that were mistakenly encrypted with repeated portions of a one-time pad over several decades. 

# 2.3 Limitations of Perfect Secrecy

We ended the previous section by noting some drawbacks of the one-time pad encryption scheme. Here, we show that these drawbacks are not specific to that scheme, but are instead inherent limitations of perfect secrecy. Specifically, we prove that any perfectly secret encryption scheme must have a key space that is at least as large as the message space. If all keys are the same length, and the message space consists of all strings of some fixed length, this implies that the key is at least as long as the message. In particular, the key length of the one-time pad is optimal. (The other limitation—namely, that the key can be used only once—is also inherent if perfect secrecy is required; see Exercise 2.13.) 

THEOREM 2.10 If (Gen, Enc, Dec) is a perfectly secret encryption scheme with message space M and key space $\kappa$ , then $| \kappa | \geq | \mathcal { M } |$ . 

PROOF We show that if $| \kappa | < | \mathcal { M } |$ then the scheme cannot be perfectly secret. Assume $| \kappa | < | \mathcal { M } |$ . Consider the uniform distribution over $\mathcal { M }$ and let $c \in { \mathcal { C } }$ be a ciphertext that occurs with non-zero probability. Let $\mathcal M ( c )$ be the set of all possible messages that are possible decryptions of $c$ ; that is 

$$
\mathcal {M} (c) \stackrel {\mathrm {d e f}} {=} \left\{m \mid m = \operatorname {D e c} _ {k} (c) \text {f o r s o m e} k \in \mathcal {K} \right\}.
$$

Clearly $| \mathcal { M } ( c ) | \leq | \mathcal { K } |$ . (Recall that we may assume Dec is deterministic.) If $| \kappa | < | \mathcal { M } |$ , there is some $m ^ { \prime } \in \mathcal { M }$ such that $m ^ { \prime } \notin \mathcal { M } ( c )$ . But then 

$$
\operatorname * {P r} [ M = m ^ {\prime} \mid C = c ] = 0 \neq \operatorname * {P r} [ M = m ^ {\prime} ],
$$

and so the scheme is not perfectly secret. 

Perfect secrecy with shorter keys? The above theorem shows an inherent limitation of schemes that achieve perfect secrecy. Even so, individuals occasionally claim they have developed a radically new encryption scheme that is “unbreakable” and achieves the security of the one-time pad without using keys as long as what is being encrypted. The above proof demonstrates that such claims cannot be true; anyone making such claims either knows very little about cryptography or is blatantly lying. 

# 2.4 *Shannon’s Theorem

In his work on perfect secrecy, Shannon also provided a characterization of perfectly secret encryption schemes. This characterization says that, under certain conditions, the key-generation algorithm Gen must choose the key uniformly from the set of all possible keys (as in the one-time pad); moreover, for every message $m$ and ciphertext $c$ there is a unique key mapping $m$ to $c$ (again, as in the one-time pad). Beyond being interesting in its own right, this theorem is a useful tool for proving (or disproving) perfect secrecy of suggested schemes. We discuss this further after the proof. 

The theorem as stated here assumes $| \mathcal { M } | = | \mathcal { K } | = | \mathcal { C } |$ , meaning that the sets of plaintexts, keys, and ciphertexts all have the same size. We have already seen that for perfect secrecy we must have $| \kappa | \geq | \mathcal { M } |$ . It is easy to see that correct decryption requires $| { \mathcal { C } } | \geq | { \mathcal { M } } |$ . Therefore, in some sense, encryption schemes with $| \mathcal { M } | = | \mathcal { K } | = | \mathcal { C } |$ are “optimal.” 

THEOREM 2.11 (Shannon’s theorem) Let (Gen, Enc, Dec) be an encryption scheme with message space $\mathcal { M }$ , for which $| \mathcal { M } | = | \mathcal { K } | = | \mathcal { C } |$ . The scheme is perfectly secret if and only if: 

1. Every key $k \in \kappa$ is chosen with (equal) probability $1 / | \mathcal { K } |$ by algorithm Gen. 

2. For every $m \in \mathcal { M }$ and every $c \in { \mathcal { C } }$ , there exists a unique key $k \in \kappa$ such that $\mathsf { E n c } _ { k } ( m )$ outputs $c$ . 

PROOF The intuition behind the proof is as follows. To see that the stated conditions imply perfect secrecy, note that condition 2 means that any ciphertext $c$ could be the result of encrypting any possible plaintext $m$ , because there is some key $k$ mapping $_ { \mathbf { \nabla } ^ { \prime } \mathbf { \nabla } ^ { \prime } } \psi _ { \mathbf { \nabla } ^ { \prime } }$ to $c$ . Since there is a unique such key, and each key is chosen with equal probability, perfect secrecy follows as for the one-time pad. For the other direction, perfect secrecy immediately implies that for every $m$ and $c$ there is at least one key mapping $m$ to $c$ . The fact that $| \mathcal { M } | = | \mathcal { K } | = | \mathcal { C } |$ means, moreover, that for every $m$ and $c$ there is exactly one such key. Given this, each key must be chosen with equal probability or else perfect secrecy would fail to hold. A formal proof follows. 

We assume for simplicity that Enc is deterministic. (One can show that this is without loss of generality here.) We first prove that if the encryption scheme satisfies conditions 1 and 2, then it is perfectly secret. The proof is essentially the same as the proof of perfect secrecy for the one-time pad, so we will be relatively brief. Fix arbitrary $c \in { \mathcal { C } }$ and $m \in \mathcal { M }$ . Let $k$ be the unique key, guaranteed by condition 2, for which $\mathtt { E n c } _ { k } ( m ) = c$ . Then, 

$$
\Pr \left[ C = c \mid M = m \right] = \Pr \left[ K = k \right] = 1 / | \mathcal {K} |,
$$

where the final equality holds by condition 1. So 

$$
\operatorname * {P r} [ C = c ] = \sum_ {m \in \mathcal {M}} \operatorname * {P r} [ \mathsf {E n c} _ {K} (m) = c ] \cdot \operatorname * {P r} [ M = m ] = 1 / | \mathcal {K} |.
$$

This holds for any distribution over $\mathcal { M }$ . Thus, for any distribution over $\mathcal { M }$ , any $m \in \mathcal { M }$ with $\operatorname* { P r } [ M = m ] \neq 0$ , and any $c \in { \mathcal { C } }$ , we have: 

$$
\begin{array}{l} \Pr [ M = m \mid C = c ] = \frac {\Pr [ C = c \mid M = m ] \cdot \Pr [ M = m ]}{\Pr [ C = c ]} \\ = \frac {\Pr [ \mathsf {E n c} _ {K} (m) = c ] \cdot \Pr [ M = m ]}{\Pr [ C = c ]} \\ = \frac {| \mathcal {K} | ^ {- 1} \cdot \Pr [ M = m ]}{| \mathcal {K} | ^ {- 1}} = \Pr [ M = m ], \\ \end{array}
$$

and the scheme is perfectly secret. 

For the second direction, assume the encryption scheme is perfectly secret; we show that conditions 1 and 2 hold. Fix arbitrary $c \in { \mathcal { C } }$ . There must be some message $m ^ { * }$ for which $\operatorname* { P r } [ \mathsf { E n c } _ { K } ( m ^ { * } ) = c ] \neq 0$ . Lemma 2.4 then implies that $\mathrm { P r } [ \mathsf { E n c } _ { K } ( m ) = c ] \neq 0$ for every $m \in \mathcal { M }$ . In other words, if we let $\mathcal { M } = \{ m _ { 1 } , m _ { 2 } , . . . \}$ , then for each $m _ { i } \in \mathcal { M }$ we have a nonempty set of keys $\kappa _ { i } \subset \kappa$ such that $\mathsf { E n c } _ { k } ( m _ { i } ) = c$ if and only if $k \in \mathcal { K } _ { i }$ . Moreover, when $i \neq j$ then $\chi _ { i }$ and $\kappa _ { j }$ must be disjoint or else correctness fails to hold. Since $| \kappa | = | \mathcal { M } |$ , we see that each $\boldsymbol { \mathrm { \chi } } _ { i }$ contains only a single key $k _ { i }$ , as required by condition 2. Now, Lemma 2.4 shows that for any $m _ { i } , m _ { j } \in { \mathcal { M } }$ we have 

$$
\Pr [ K = k _ {i} ] = \Pr [ \mathsf {E n c} _ {K} (m _ {i}) = c ] = \Pr [ \mathsf {E n c} _ {K} (m _ {j}) = c ] = \Pr [ K = k _ {j} ].
$$

Since this holds for all $1 \leq i , j \leq | { \mathcal { M } } | = | { \mathcal { K } } |$ , and $k _ { i } \neq k _ { j }$ for $i \neq j$ , this means each key is chosen with probability $1 / | \mathcal { K } |$ , as required by condition 1. 

Shannon’s theorem is useful for deciding whether a given scheme is perfectly secret. Condition 1 is easy to check, and condition 2 can be demonstrated (or contradicted) without having to compute any probabilities (in contrast to working with Definition 2.3 directly). As an example, perfect secrecy of the one-time pad is trivial to prove using Shannon’s theorem. We stress, however, that the theorem only applies when $| \mathcal { M } | = | \mathcal { K } | = | \mathcal { C } |$ . 

# References and Additional Reading

The one-time pad is popularly credited to Vernam [172], who filed a patent on it, but recent historical research [25] shows that it was invented some 

35 years earlier. Analysis of the one-time pad had to await the groundbreaking work of Shannon [154], who introduced the notion of perfect secrecy. 

In this chapter we studied perfectly secret encryption. Some other cryptographic problems can also be solved with “perfect” security. A notable example is the problem of message authentication where the aim is to prevent an adversary from (undetectably) modifying a message sent from one party to another. We study this problem in depth in Chapter 4, discussing “perfectly secure” message authentication in Section 4.6. 

# Exercises

2.1 Prove that, by redefining the key space, we may assume that the keygeneration algorithm Gen chooses a key uniformly at random from the key space, without changing $\operatorname* { P r } [ C = c \mid M = m ]$ for any $m , c$ . 

Hint: Define the key space to be the set of all possible random tapes for the randomized algorithm Gen. 

2.2 Prove that, by redefining the key space, we may assume that Enc is deterministic without changing $\operatorname* { P r } [ C = c \mid M = m ]$ for any $m , c$ . 

2.3 Prove or refute: An encryption scheme with message space $\mathcal { M }$ is perfectly secret if and only if for every probability distribution over $\mathcal { M }$ and every $c _ { 0 } , c _ { 1 } \in \mathcal { C }$ we have $\operatorname* { P r } [ C = c _ { 0 } ] = \operatorname* { P r } [ C = c _ { 1 } ]$ . 

2.4 Prove the second direction of Lemma 2.4. 

2.5 Prove Lemma 2.6. 

2.6 For each of the following encryption schemes, state whether the scheme is perfectly secret. Justify your answer in each case. 

(a) The message space is $\mathcal { M } = \{ 0 , . . . , 4 \}$ . Algorithm Gen chooses a uniform key from the key space $\{ 0 , \ldots , 5 \}$ . $\mathsf { E n c } _ { k } ( m )$ returns [k + m mod 5], and $\mathsf { D e c } _ { k } ( c )$ returns $[ c - k$ mod 5]. 

(b) The message space is $\mathcal { M } = \{ m \in \{ 0 , 1 \} ^ { \ell } \ |$ the last bit of $m$ is $0 \}$ Gen chooses a uniform key from $\{ 0 , 1 \} ^ { \ell - 1 }$ . $\mathsf { E n c } _ { k } ( m )$ returns ciphertext $m \oplus ( k \lVert { \boldsymbol { 0 } } )$ , and $\mathsf { D e c } _ { k } ( c )$ returns $c \oplus ( k \| 0 )$ . 

2.7 When using the one-time pad with the key $k = 0 ^ { \ell }$ , we have $\mathsf { E n c } _ { k } ( m ) =$ $k \oplus m = m$ and the message is sent in the clear! It has therefore been suggested to modify the one-time pad by only encrypting with $k \neq 0 ^ { \ell }$ (i.e., to have Gen choose $k$ uniformly from the set of nonzero keys of length $\ell$ ). Is this modified scheme still perfectly secret? Explain. 

2.8 Let $\mathrm { I I }$ denote the Vigen`ere cipher where the message space consists of all 3-character strings (over the English alphabet), and the key is generated by first choosing the period $t$ uniformly from $\{ 1 , 2 , 3 \}$ and then letting the key be a uniform string of length $t$ . 

(a) Define $\boldsymbol { A }$ as follows: $\mathcal { A }$ outputs $m _ { 0 } = \mathsf { a a b }$ and $m _ { 1 } = \mathsf { a b b }$ . When given a ciphertext $c$ , it outputs 0 if the first character of $c$ is the pute same as the second character of $\mathrm { P r } [ \mathsf { P r i v } \mathsf { K } _ { \mathcal { A , \Pi } } ^ { \mathsf { e a v } } = 1 ]$ ]. $c$ , and outputs 1 otherwise. Com-

(b) Construct and analyze an adversary $\mathcal { A } ^ { \prime }$ for which $\mathrm { P r } [ \mathsf { P r i v } \mathsf { K } _ { \mathcal { A } ^ { \prime } , \Pi } ^ { \mathsf { e a v } } = 1 ]$ is greater than your answer from part (a). 

2.9 In this exercise, we look at different conditions under which the shift, mono-alphabetic substitution, and Vigen`ere ciphers are perfectly secret: 

(a) Prove that if only a single character is encrypted, then the shift cipher is perfectly secret. 

(b) What is the largest message space $\mathcal { M }$ for which the mono-alphabetic substitution cipher provides perfect secrecy? 

(c) Prove that the Vigen`ere cipher using (fixed) period $t$ is perfectly secret when used to encrypt messages of length $t$ . 

Reconcile this with the attacks shown in the previous chapter. 

2.10 Prove that a scheme satisfying Definition 2.5 must have $| \mathcal { K } | \ge | \mathcal { M } |$ scheme with without using Lemma 2.4. Specifically, let $| \kappa | < | \mathcal { M } |$ . Show an $\boldsymbol { A }$ for which $\mathrm { I I }$ be an arbitrary encryption $\begin{array} { r } { \operatorname* { P r } \left[ \mathsf { P r i v } \mathsf { K } _ { \mathcal { A , \Pi } } ^ { \mathsf { e a v } } = 1 \right] > \frac { 1 } { 2 } } \end{array}$ . 

Hint: It may be easier to let $\mathcal { A }$ be randomized. 

2.11 Assume we require only that an encryption scheme (Gen, Enc, Dec) with message space $\mathcal { M }$ satisfy the following: For all $m \in \mathcal { M }$ , we have $\operatorname* { P r } [ \mathtt { D e c } _ { K } ( \mathtt { E n c } _ { K } ( m ) ) = m ] \ge 2 ^ { - t }$ . (This probability is taken over choice of the key as well as any randomness used during encryption.) Show that perfect secrecy can be achieved with $| \kappa | < | \mathcal { M } |$ when $t \geq 1$ . Prove a lower bound on the size of $\kappa$ in terms of $t$ . 

2.12 Let $\varepsilon \geq 0$ be a constant. Say an encryption scheme is $\varepsilon$ -perfectly secret if for every adversary $\boldsymbol { A }$ it holds that 

$$
\Pr \left[ \operatorname {P r i v} K _ {\mathcal {A}, \Pi} ^ {\mathrm {e a v}} = 1 \right] \leq \frac {1}{2} + \varepsilon .
$$

(Compare to Definition 2.5.) Show that $\varepsilon$ -perfect secrecy can be achieved with $| \kappa | < | \mathcal { M } |$ when $\varepsilon > 0$ . Prove a lower bound on the size of $\kappa$ in terms of $\varepsilon$ . 

2.13 In this problem we consider definitions of perfect secrecy for the encryption of two messages (using the same key). Here we consider distributions over pairs of messages from the message space $\mathcal { M }$ ; we let $M _ { 1 } , M _ { 2 }$ be random variables denoting the first and second message, respectively. (We stress that these random variables are not assumed to be independent.) We generate a (single) key $k$ , sample a pair of messages $( m _ { 1 } , m _ { 2 } )$ according to the given distribution, and then compute ciphertexts $c _ { 1 } \gets \mathsf { E n c } _ { k } ( m _ { 1 } )$ and $c _ { 2 } \gets \mathsf { E n c } _ { k } ( m _ { 2 } )$ ; this induces a distribution over pairs of ciphertexts and we let $C _ { 1 } , C _ { 2 }$ be the corresponding random variables. 

(a) Say encryption scheme (Gen, Enc, Dec) is perfectly secret for two messages if for all distributions over ${ \mathcal { M } } \times { \mathcal { M } }$ , all $m _ { 1 } , m _ { 2 } \in { \mathcal { M } }$ , and all ciphertexts $c _ { 1 } , c _ { 2 } \in \mathcal { C }$ with $\mathrm { P r } [ C _ { 1 } = c _ { 1 } \land C _ { 2 } = c _ { 2 } ] > 0$ : 

$$
\begin{array}{l} \Pr \left[ M _ {1} = m _ {1} \wedge M _ {2} = m _ {2} \mid C _ {1} = c _ {1} \wedge C _ {2} = c _ {2} \right] \\ = \Pr [ M _ {1} = m _ {1} \wedge M _ {2} = m _ {2} ]. \\ \end{array}
$$

Prove that no encryption scheme can satisfy this definition. 

Hint: Take $c _ { 1 } = c _ { 2 }$ 

(b) Say encryption scheme (Gen, Enc, Dec) is perfectly secret for two distinct messages if for all distributions over $\mathcal { M } \times \mathcal { M }$ where the first and second messages are guaranteed to be different (i.e., distributions over pairs of distinct messages), all $m _ { 1 } , m _ { 2 } \in { \mathcal { M } }$ , and all $c _ { 1 } , c _ { 2 } \in \mathcal { C }$ with $\mathrm { P r } [ C _ { 1 } = c _ { 1 } \land C _ { 2 } = c _ { 2 } ] > 0$ : 

$$
\begin{array}{l} \Pr \left[ M _ {1} = m _ {1} \wedge M _ {2} = m _ {2} \mid C _ {1} = c _ {1} \wedge C _ {2} = c _ {2} \right] \\ = \Pr \left[ M _ {1} = m _ {1} \wedge M _ {2} = m _ {2} \right]. \\ \end{array}
$$

Show an encryption scheme that provably satisfies this definition. 

Hint: The encryption scheme you propose need not be efficient, although an efficient solution is possible. 
